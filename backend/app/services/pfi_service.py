import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.reputation import ReputationScore

logger = logging.getLogger("app.pfi")

PFI_MIN, PFI_MAX, PFI_RANGE = 300, 850, 550

TIERS = [
    (750, "Platinum", "💎", "Top freelancer — exceptional and trusted"),
    (650, "Gold",     "🥇", "Highly reliable with consistent quality"),
    (500, "Silver",   "🥈", "Solid performer with a growing track record"),
    (300, "Bronze",   "🥉", "Building reputation — keep delivering quality"),
]

def _tier(score: float) -> dict:
    for threshold, name, icon, desc in TIERS:
        if score >= threshold:
            return {"name": name, "icon": icon, "description": desc, "threshold": threshold}
    return {"name": "Bronze", "icon": "🥉", "description": "Building reputation", "threshold": 300}

def _next_tier(score: float) -> dict | None:
    for threshold, name, icon, desc in reversed(TIERS):
        if threshold > score:
            return {"name": name, "icon": icon, "threshold": threshold, "points_needed": round(threshold - score, 1)}
    return None

def get_score_breakdown(rep: ReputationScore) -> dict:
    tier = _tier(rep.pfi_score)
    return {
        "pfi_score": round(rep.pfi_score, 1),
        "tier": tier,
        "next_tier": _next_tier(rep.pfi_score),
        "formula": "PFI = 300 + 550 × (40%·success + 30%·quality + 20%·on_time + 10%·dispute_free)",
        "score_breakdown": {
            "success_rate": {
                "value": round(rep.milestone_success_rate, 4),
                "display": f"{round(rep.milestone_success_rate * 100, 1)}%",
                "weight": "40%",
                "contribution": round(PFI_RANGE * 0.40 * rep.milestone_success_rate, 1),
            },
            "quality_score": {
                "value": round(rep.avg_quality_score, 4),
                "display": f"{round(rep.avg_quality_score * 100, 1)}%",
                "weight": "30%",
                "contribution": round(PFI_RANGE * 0.30 * rep.avg_quality_score, 1),
            },
            "deadline_adherence": {
                "value": round(rep.deadline_adherence_rate, 4),
                "display": f"{round(rep.deadline_adherence_rate * 100, 1)}%",
                "weight": "20%",
                "contribution": round(PFI_RANGE * 0.20 * rep.deadline_adherence_rate, 1),
            },
            "dispute_rate": {
                "value": round(rep.dispute_rate, 4),
                "display": f"{round(rep.dispute_rate * 100, 1)}%",
                "weight": "10% (inverted)",
                "contribution": round(PFI_RANGE * 0.10 * (1 - rep.dispute_rate), 1),
            },
        },
        "stats": {
            "total_milestones": rep.total_milestones,
            "successful_milestones": rep.successful_milestones,
            "history_entries": len(rep.score_history or []),
        },
        "recent_history": (rep.score_history or [])[-5:],
    }


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

        old_score = rep.pfi_score

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
            "milestone_n": rep.total_milestones,
            "pfi_score": rep.pfi_score,
            "delta": round(rep.pfi_score - old_score, 1),
            "milestone_success": milestone_success,
            "quality_score": round(quality_score, 3),
            "on_time": on_time,
            "disputed": disputed,
        }
        if rep.score_history is None:
            rep.score_history = []
        rep.score_history = rep.score_history + [history_entry]

        rep.updated_at = datetime.utcnow()
        await self.db.flush()
        logger.info(f"PFI {freelancer_id}: {old_score:.1f} → {rep.pfi_score:.1f} (Δ{rep.pfi_score-old_score:+.1f})")
        return rep

    async def get_breakdown(self, freelancer_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(ReputationScore).where(ReputationScore.user_id == freelancer_id)
        )
        rep = result.scalar_one_or_none()
        if not rep:
            return {
                "pfi_score": 500.0,
                "tier": _tier(500),
                "next_tier": _next_tier(500),
                "formula": "PFI = 300 + 550 × (40%·success + 30%·quality + 20%·on_time + 10%·dispute_free)",
                "score_breakdown": {},
                "stats": {"total_milestones": 0, "successful_milestones": 0, "history_entries": 0},
                "recent_history": [],
            }
        return get_score_breakdown(rep)
