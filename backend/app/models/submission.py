import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class SubmissionType(str, enum.Enum):
    code = "code"
    content = "content"
    design = "design"
    link = "link"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    freelancer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submission_type: Mapped[SubmissionType] = mapped_column(SAEnum(SubmissionType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)  # text/url/code snippet
    repo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    file_paths: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone", back_populates="submissions")
    freelancer = relationship("User", back_populates="submissions")
    evaluation = relationship("Evaluation", back_populates="submission", uselist=False)
