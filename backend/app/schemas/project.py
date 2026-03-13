from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Any


class ProjectType(str, Enum):
    web_application = "web_application"
    mobile_app = "mobile_app"
    api = "api"
    content = "content"
    design = "design"
    data_science = "data_science"
    other = "other"


class ProjectStatus(str, Enum):
    draft = "draft"
    active = "active"
    in_progress = "in_progress"
    completed = "completed"
    disputed = "disputed"
    cancelled = "cancelled"


class ProjectCreate(BaseModel):
    title: str
    description: str
    total_budget: float
    project_type: ProjectType | None = None  # AI will detect if omitted


class MilestoneOut(BaseModel):
    id: UUID
    title: str
    description: str
    order_index: int
    deadline_days: int
    payment_amount: float
    status: str
    release_status: str

    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: UUID
    title: str
    description: str
    project_type: str
    status: ProjectStatus
    total_budget: float
    employer_id: UUID
    freelancer_id: UUID | None
    ai_roadmap: dict[str, Any] | None
    milestones: list[MilestoneOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectAssign(BaseModel):
    freelancer_id: UUID
