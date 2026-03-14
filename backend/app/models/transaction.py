import uuid
from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, DateTime, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    lock = "lock"
    release = "release"
    refund = "refund"
    platform_fee = "platform_fee"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    reversed = "reversed"


class EscrowAccount(Base):
    __tablename__ = "escrow_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    total_deposited: Mapped[float] = mapped_column(Float, default=0.0)
    locked_balance: Mapped[float] = mapped_column(Float, default=0.0)
    released_balance: Mapped[float] = mapped_column(Float, default=0.0)
    refunded_balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="escrow")
    user = relationship("User", back_populates="escrow_account")
    transactions = relationship("Transaction", back_populates="escrow_account", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    escrow_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("escrow_accounts.id"), nullable=False)
    milestone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType, name="transaction_type", create_type=False), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(SAEnum(TransactionStatus, name="transaction_status", create_type=False), default=TransactionStatus.pending)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    escrow_account = relationship("EscrowAccount", back_populates="transactions")
