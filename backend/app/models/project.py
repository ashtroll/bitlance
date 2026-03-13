import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SAEnum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    in_progress = "in_progress"
    completed = "completed"
    disputed = "disputed"
    cancelled = "cancelled"


class ProjectType(str, enum.Enum):
    web_application = "web_application"
    mobile_app = "mobile_app"
    api = "api"
    content = "content"
    design = "design"
    data_science = "data_science"
    other = "other"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[ProjectType] = mapped_column(SAEnum(ProjectType), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus), default=ProjectStatus.draft)
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    employer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    freelancer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ai_roadmap: Mapped[dict] = mapped_column(JSONB, nullable=True)  # raw AI output
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employer = relationship("User", back_populates="projects_as_employer", foreign_keys=[employer_id])
    freelancer = relationship("User", back_populates="projects_as_freelancer", foreign_keys=[freelancer_id])
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    escrow = relationship("EscrowAccount", back_populates="project", uselist=False)
