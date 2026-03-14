import json
import re
from typing import Optional

from app.config import settings
from app.ai.prompts import MILESTONE_GENERATION_PROMPT


class MilestoneGenerator:
    """Converts natural language project descriptions into structured milestone roadmaps."""

    def __init__(self):
        self.model = settings.ai_model
        self._client = None

    def _get_client(self):
        if self._client is not None:
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
            raise ValueError("No AI API key configured.")

        return self._client

    async def generate(self, description: str, project_type: Optional[str] = None, budget: float = 0,
                       tech_stack: list = None, language_preferences: str = "",
                       system_requirements: str = "", special_notes: str = "") -> dict:
        """Generate a structured milestone roadmap from a project description."""
        client = self._get_client()

        prompt = MILESTONE_GENERATION_PROMPT.format(
            description=description,
            budget=budget,
            project_type=project_type or "auto-detect",
            tech_stack=", ".join(tech_stack) if tech_stack else "Not specified",
            language_preferences=language_preferences or "None",
            system_requirements=system_requirements or "None",
            special_notes=special_notes or "None",
        )

        try:
            if self._provider == "openai":
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a technical project manager. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
            else:
                # Anthropic
                response = await client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                raw = response.content[0].text

            return self._parse_response(raw)

        except Exception as e:
            # Fallback: return a basic structure
            return self._fallback_roadmap(description, project_type)

    def _parse_response(self, raw: str) -> dict:
        """Extract and validate JSON from AI response."""
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        # Extract JSON object if surrounded by extra text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        data = json.loads(raw)

        # Normalize budget_weight to sum to exactly 1.0
        milestones = data.get("milestones", [])
        if milestones:
            total_w = sum(m.get("budget_weight", 0) for m in milestones)
            if total_w <= 0:
                eq = round(1.0 / len(milestones), 4)
                for m in milestones:
                    m["budget_weight"] = eq
            elif abs(total_w - 1.0) > 0.01:
                for m in milestones:
                    m["budget_weight"] = round(m.get("budget_weight", 1.0 / len(milestones)) / total_w, 4)
            # Fix rounding so they sum to exactly 1.0
            total_after = sum(m["budget_weight"] for m in milestones)
            if milestones and abs(total_after - 1.0) > 0.001:
                milestones[-1]["budget_weight"] = round(milestones[-1]["budget_weight"] + (1.0 - total_after), 4)

        # Validate required keys
        if "milestones" not in data:
            raise ValueError("AI response missing 'milestones' key")
        if not isinstance(data["milestones"], list):
            raise ValueError("'milestones' must be a list")

        return data

    def _fallback_roadmap(self, description: str, project_type: Optional[str]) -> dict:
        """Return a generic roadmap when AI is unavailable."""
        return {
            "project_type": project_type or "other",
            "complexity": "medium",
            "estimated_total_days": 21,
            "milestones": [
                {
                    "title": "Project Setup & Architecture",
                    "description": "Initialize repository, set up development environment, define architecture",
                    "deadline_days": 3,
                    "budget_weight": 0.25,
                    "acceptance_criteria": ["Repository created", "README documented", "Dev environment working"],
                    "deliverable_type": "code",
                },
                {
                    "title": "Core Feature Implementation",
                    "description": f"Implement the main features described: {description[:200]}",
                    "deadline_days": 10,
                    "budget_weight": 0.25,
                    "acceptance_criteria": ["Core features working", "Unit tests passing"],
                    "deliverable_type": "code",
                },
                {
                    "title": "Testing & Deployment",
                    "description": "Write tests, fix bugs, and deploy to staging environment",
                    "deadline_days": 5,
                    "budget_weight": 0.25,
                    "acceptance_criteria": ["Test coverage > 70%", "Deployed to staging", "No critical bugs"],
                    "deliverable_type": "code",
                },
                {
                    "title": "Final Delivery & Documentation",
                    "description": "Complete documentation and final delivery",
                    "deadline_days": 3,
                    "budget_weight": 0.25,
                    "acceptance_criteria": ["Documentation complete", "Client handover done"],
                    "deliverable_type": "documentation",
                },
            ],
        }
