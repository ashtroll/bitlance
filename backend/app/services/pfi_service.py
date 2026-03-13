import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.reputation import ReputationScore


class PFIService:
    """
    Professional Fidelity Index — reputation scoring engine.

    Formula:
        PFI = 0.4 * milestone_success_rate
            + 0.3 * avg_quality_score
            + 0.2 * deadline_adherence_rate
            + 0.1 * (1 - dispute_rate)

    Scaled to 300–850 range.
    """

    PFI_MIN = 300
    PFI_MAX = 850
    PFI_RANGE = 550  # 850 - 300

    WEIGHTS = {
        "success_rate": 0.40,
        "quality_score": 0.30,
        "deadline_adherence": 0.20,
        "dispute_rate": 0.10,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_score(
        self,
        freelancer_id: uuid.UUID,
        milestone_success: bool,
        quality_score: float,
        on_time: bool,
        disputed: bool,
    ) -> ReputationScore:
        """Recalculate and persist PFI after a milestone event."""

        result = await self.db.execute(
            select(ReputationScore).where(ReputationScore.user_id == freelancer_id)
        )
        rep = result.scalar_one_or_none()

        if not rep:
            rep = ReputationScore(user_id=freelancer_id)
            self.db.add(rep)
            await self.db.flush()

        # Update counters
        rep.total_milestones += 1
        if milestone_success:
            rep.successful_milestones += 1
        if on_time:
            rep.on_time_milestones += 1
        if disputed:
            rep.disputed_milestones += 1

        # Recalculate rates
        rep.milestone_success_rate = rep.successful_milestones / rep.total_milestones
        rep.deadline_adherence_rate = rep.on_time_milestones / rep.total_milestones
        rep.dispute_rate = rep.disputed_milestones / rep.total_milestones

        # Update rolling average quality score
        n = rep.total_milestones
        rep.avg_quality_score = (
            (rep.avg_quality_score * (n - 1) + quality_score) / n
        )

        # Compute raw PFI (0.0 to 1.0)
        raw_pfi = (
            self.WEIGHTS["success_rate"] * rep.milestone_success_rate
            + self.WEIGHTS["quality_score"] * rep.avg_quality_score
            + self.WEIGHTS["deadline_adherence"] * rep.deadline_adherence_rate
            + self.WEIGHTS["dispute_rate"] * (1 - rep.dispute_rate)
        )

        # Scale to 300–850
        rep.pfi_score = round(self.PFI_MIN + raw_pfi * self.PFI_RANGE, 1)

        # Append to history
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "pfi_score": rep.pfi_score,
            "milestone_success": milestone_success,
            "quality_score": quality_score,
            "on_time": on_time,
            "disputed": disputed,
        }
        if rep.score_history is None:
            rep.score_history = []
        rep.score_history = rep.score_history + [history_entry]

        rep.updated_at = datetime.utcnow()
        await self.db.flush()
        return rep
