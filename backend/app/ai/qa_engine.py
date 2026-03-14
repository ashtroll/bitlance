import json
import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.submission import Submission, SubmissionType
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.evaluation import Evaluation, CompletionStatus
from app.ai.prompts import CODE_REVIEW_PROMPT, CONTENT_RUBRIC_PROMPT, DESIGN_REVIEW_PROMPT
from app.ai.code_evaluator import CodeEvaluator
import logging
logger = logging.getLogger("app.qa_engine")


class QAEngine:
    """Orchestrates automated quality assurance for milestone submissions."""

    def __init__(self):
        self._client = None
        self._provider = None

    def _get_client(self):
        if self._client:
            return self._client
        if settings.grok_api_key:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=settings.grok_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            self._provider = "openai"
        elif settings.openai_api_key:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            self._provider = "openai"
        elif settings.anthropic_api_key:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self._provider = "anthropic"
        else:
            raise ValueError("No AI API key configured")
        return self._client

    async def evaluate(
        self,
        submission: Submission,
        milestone: Milestone,
        project: Project,
        db: AsyncSession,
    ) -> Evaluation:
        """Route submission to appropriate evaluator based on type."""
        logger.info(f"Evaluating submission {submission.id} type={submission.submission_type}")
        try:
            if submission.submission_type == SubmissionType.code:
                result = await self._evaluate_code(submission, milestone)
            elif submission.submission_type in (SubmissionType.content, SubmissionType.link):
                result = await self._evaluate_content(submission, milestone)
            else:
                result = await self._evaluate_design(submission, milestone)
        except Exception as e:
            logger.error(f"Evaluation routing failed: {e}", exc_info=True)
            result = self._fallback_result(str(e))

        # Sanitize
        result.setdefault("completion_status", "partial")
        result.setdefault("confidence_score", 0.55)
        result.setdefault("quality_score", result["confidence_score"])
        result.setdefault("feedback", "Automated evaluation completed.")
        result["confidence_score"] = max(0.0, min(1.0, float(result["confidence_score"])))
        result["quality_score"] = max(0.0, min(1.0, float(result["quality_score"])))
        if result["completion_status"] not in {"complete", "partial", "failed"}:
            result["completion_status"] = "partial"

        evaluation = Evaluation(
            milestone_id=milestone.id,
            submission_id=submission.id,
            completion_status=CompletionStatus(result["completion_status"]),
            confidence_score=result["confidence_score"],
            quality_score=result["quality_score"],
            feedback=result.get("feedback", ""),
            test_results=result.get("test_results"),
            llm_review=result,
            auto_approved=False,
        )
        db.add(evaluation)
        await db.flush()
        logger.info(f"Evaluation done: {result['completion_status']} confidence={result['confidence_score']:.2f}")
        return evaluation

    async def _evaluate_code(self, submission: Submission, milestone: Milestone) -> dict:
        """Run code evaluation: sandbox tests + LLM review."""
        test_results = None
        if submission.repo_url:
            try:
                code_eval = CodeEvaluator()
                test_results = await code_eval.run_tests(submission.repo_url)
                logger.info(f"Sandbox results: {test_results}")
            except Exception as e:
                logger.warning(f"Sandbox failed (non-fatal): {e}")
                test_results = {"error": str(e), "passed": False, "tests_run": 0}

        result = await self._llm_review(
            submission, milestone, CODE_REVIEW_PROMPT,
            extra={"test_results": json.dumps(test_results) if test_results else "No sandbox tests run",
                   "verification_method": "automated_tests"}
        )
        result["test_results"] = test_results

        if test_results and test_results.get("passed") and test_results.get("tests_run", 0) > 0:
            result["confidence_score"] = min(1.0, result.get("confidence_score", 0.5) + 0.08)
        elif test_results and not test_results.get("passed") and not test_results.get("error"):
            result["confidence_score"] = min(0.65, result.get("confidence_score", 0.5))

        return result

    async def _evaluate_content(self, submission: Submission, milestone: Milestone) -> dict:
        """Evaluate content submissions with LLM rubric scoring."""
        return await self._llm_review(submission, milestone, CONTENT_RUBRIC_PROMPT)

    async def _evaluate_design(self, submission: Submission, milestone: Milestone) -> dict:
        """Evaluate design submissions using LLM heuristic scoring."""
        return await self._llm_review(submission, milestone, DESIGN_REVIEW_PROMPT)

    async def _llm_review(self, submission: Submission, milestone: Milestone,
                          prompt_template: str, extra: dict = None) -> dict:
        """Call LLM with structured prompt and parse JSON response."""
        acceptance = getattr(milestone, "acceptance_criteria", []) or []
        if isinstance(acceptance, dict):
            acceptance = acceptance.get("criteria", [])

        vars_ = {
            "milestone_title": milestone.title,
            "milestone_description": milestone.description,
            "acceptance_criteria": json.dumps(acceptance, indent=2),
            "repo_url": submission.repo_url or "N/A",
            "content": (submission.content or "")[:3000] or "See repo URL",
            "test_results": "N/A",
            "verification_method": "content_rubric",
        }
        if extra:
            vars_.update(extra)

        try:
            prompt = prompt_template.format(**vars_)
        except KeyError:
            prompt = prompt_template.format_map({**vars_, **{k: "" for k in ["test_results", "verification_method"]}})

        try:
            client = self._get_client()
            if self._provider == "openai":
                response = await client.chat.completions.create(
                    model=settings.ai_model,
                    messages=[
                        {"role": "system", "content": "You are a precise QA evaluator. Always respond with valid JSON only. No markdown outside JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                )
                raw = response.choices[0].message.content
            else:
                response = await client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text

            raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                raw = match.group(0)
            return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.warning(f"LLM returned invalid JSON: {e}")
            return self._fallback_result(f"JSON parse error: {e}")
        except Exception as e:
            logger.error(f"LLM review failed: {e}", exc_info=True)
            return self._fallback_result(str(e))

    def _fallback_result(self, error_msg: str) -> dict:
        return {
            "completion_status": "partial",
            "confidence_score": 0.55,
            "quality_score": 0.55,
            "feedback": f"Automated evaluation completed with reduced confidence. Note: {error_msg[:150]}. A partial score of 55% has been assigned. You may resubmit or raise a dispute.",
            "issues": [{"severity": "minor", "description": f"Evaluation system: {error_msg[:100]}"}],
            "positives": [],
            "recommendations": ["Ensure repo URL is publicly accessible", "Include clear README documentation"],
        }
