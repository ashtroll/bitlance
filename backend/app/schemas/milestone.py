from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Any


class SubmissionType(str, Enum):
    code = "code"
    content = "content"
    design = "design"
    link = "link"


class MilestoneSubmit(BaseModel):
    milestone_id: UUID
    submission_type: SubmissionType
    content: str | None = None
    repo_url: str | None = None
    notes: str | None = None


class EvaluationOut(BaseModel):
    id: UUID
    completion_status: str
    confidence_score: float
    quality_score: float | None
    feedback: str | None
    test_results: dict[str, Any] | None
    auto_approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionOut(BaseModel):
    id: UUID
    milestone_id: UUID
    submission_type: str
    content: str | None
    repo_url: str | None
    notes: str | None
    created_at: datetime
    evaluation: EvaluationOut | None = None

    model_config = {"from_attributes": True}


class MilestoneEvaluateRequest(BaseModel):
    submission_id: UUID
    force: bool = False  # bypass confidence threshold
