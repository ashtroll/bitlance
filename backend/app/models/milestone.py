import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, DateTime, Date, Float, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class MilestoneStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    paid = "paid"


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    deadline_days: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=True)
    payment_amount: Mapped[float] = mapped_column(Float, nullable=False)
    locked_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[MilestoneStatus] = mapped_column(SAEnum(MilestoneStatus), default=MilestoneStatus.pending)
    release_status: Mapped[str] = mapped_column(String(50), default="locked")  # locked|released|refunded
    payment_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")
    submissions = relationship("Submission", back_populates="milestone", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="milestone", cascade="all, delete-orphan")
