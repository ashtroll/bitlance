import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, ForeignKey, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class CompletionStatus(str, enum.Enum):
    complete = "complete"
    partial = "partial"
    failed = "failed"


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    completion_status: Mapped[CompletionStatus] = mapped_column(SAEnum(CompletionStatus), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, nullable=True)
    test_results: Mapped[dict] = mapped_column(JSONB, nullable=True)
    llm_review: Mapped[dict] = mapped_column(JSONB, nullable=True)
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone", back_populates="evaluations")
    submission = relationship("Submission", back_populates="evaluation")
