import json
import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.submission import Submission, SubmissionType
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.evaluation import Evaluation, CompletionStatus
from app.ai.prompts import CODE_REVIEW_PROMPT, CONTENT_RUBRIC_PROMPT
from app.ai.code_evaluator import CodeEvaluator


class QAEngine:
    """Orchestrates automated quality assurance for milestone submissions."""

    def __init__(self):
        self._client = None
        self._provider = None

    def _get_client(self):
        if self._client:
            return self._client
        if settings.openai_api_key:
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

        if submission.submission_type == SubmissionType.code:
            result = await self._evaluate_code(submission, milestone)
        elif submission.submission_type in (SubmissionType.content, SubmissionType.link):
            result = await self._evaluate_content(submission, milestone)
        else:
            result = await self._evaluate_design(submission, milestone)

        evaluation = Evaluation(
            milestone_id=milestone.id,
            submission_id=submission.id,
            completion_status=CompletionStatus(result["completion_status"]),
            confidence_score=result["confidence_score"],
            quality_score=result.get("quality_score", result["confidence_score"]),
            feedback=result.get("feedback", ""),
            test_results=result.get("test_results"),
            llm_review=result,
            auto_approved=False,
        )
        db.add(evaluation)
        await db.flush()
        return evaluation

    async def _evaluate_code(self, submission: Submission, milestone: Milestone) -> dict:
        """Run code evaluation: sandbox tests + static analysis + LLM review."""
        results = {"test_results": None, "static_analysis": None}

        # 1. Try Docker sandbox evaluation if repo URL provided
        if submission.repo_url:
            try:
                code_eval = CodeEvaluator()
                test_result = await code_eval.run_tests(submission.repo_url)
                results["test_results"] = test_result
            except Exception as e:
                results["test_results"] = {"error": str(e), "passed": False}

        # 2. LLM code review
        llm_result = await self._llm_review(submission, milestone, CODE_REVIEW_PROMPT)
        results.update(llm_result)

        # Blend scores: LLM is primary, tests can boost/penalize
        if results.get("test_results") and results["test_results"].get("passed"):
            results["confidence_score"] = min(1.0, results.get("confidence_score", 0.5) + 0.1)

        return results

    async def _evaluate_content(self, submission: Submission, milestone: Milestone) -> dict:
        """Evaluate content submissions with LLM rubric scoring."""
        return await self._llm_review(submission, milestone, CONTENT_RUBRIC_PROMPT)

    async def _evaluate_design(self, submission: Submission, milestone: Milestone) -> dict:
        """Placeholder for design evaluation."""
        return {
            "completion_status": "partial",
            "confidence_score": 0.5,
            "quality_score": 0.5,
            "feedback": "Design evaluation requires manual review. Placeholder score applied.",
        }

    async def _llm_review(self, submission: Submission, milestone: Milestone, prompt_template: str) -> dict:
        """Call LLM with appropriate prompt and parse structured response."""
        client = self._get_client()

        acceptance = getattr(milestone, "acceptance_criteria", [])
        if isinstance(acceptance, dict):
            acceptance = acceptance.get("criteria", [])

        prompt = prompt_template.format(
            milestone_title=milestone.title,
            milestone_description=milestone.description,
            acceptance_criteria=json.dumps(acceptance),
            repo_url=submission.repo_url or "N/A",
            content=submission.content or "See repo URL",
        )

        try:
            if self._provider == "openai":
                response = await client.chat.completions.create(
                    model=settings.ai_model,
                    messages=[
                        {"role": "system", "content": "You are a QA evaluator. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
            else:
                response = await client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text

            raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
            return json.loads(raw)

        except Exception as e:
            return {
                "completion_status": "partial",
                "confidence_score": 0.5,
                "quality_score": 0.5,
                "feedback": f"Automated evaluation encountered an error: {str(e)}. Manual review required.",
            }
