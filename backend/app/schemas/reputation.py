from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any


class ReputationOut(BaseModel):
    user_id: UUID
    pfi_score: float
    milestone_success_rate: float
    avg_quality_score: float
    deadline_adherence_rate: float
    dispute_rate: float
    total_milestones: int
    successful_milestones: int
    score_history: list[dict[str, Any]]
    updated_at: datetime

    model_config = {"from_attributes": True}
