from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class ApplicationCreate(BaseModel):
    cover_letter: str | None = None
    proposed_rate: float | None = None


class ApplicationReview(BaseModel):
    status: ApplicationStatus
    employer_note: str | None = None


class FreelancerBasic(BaseModel):
    id: UUID
    username: str
    full_name: str | None
    email: str

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: UUID
    project_id: UUID
    freelancer_id: UUID
    cover_letter: str | None
    proposed_rate: float | None
    status: ApplicationStatus
    employer_note: str | None
    created_at: datetime
    freelancer: FreelancerBasic | None = None

    model_config = {"from_attributes": True}
