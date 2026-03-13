import uuid
from datetime import datetime
from sqlalchemy import Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class ReputationScore(Base):
    __tablename__ = "reputation_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    pfi_score: Mapped[float] = mapped_column(Float, default=500.0)  # 300-850
    milestone_success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    deadline_adherence_rate: Mapped[float] = mapped_column(Float, default=0.0)
    dispute_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_milestones: Mapped[int] = mapped_column(Integer, default=0)
    successful_milestones: Mapped[int] = mapped_column(Integer, default=0)
    disputed_milestones: Mapped[int] = mapped_column(Integer, default=0)
    on_time_milestones: Mapped[int] = mapped_column(Integer, default=0)
    score_history: Mapped[list] = mapped_column(JSONB, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="reputation")
