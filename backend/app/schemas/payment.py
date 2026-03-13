from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum


class DepositRequest(BaseModel):
    project_id: UUID
    amount: float


class ReleaseRequest(BaseModel):
    milestone_id: UUID


class EscrowOut(BaseModel):
    id: UUID
    project_id: UUID
    total_deposited: float
    locked_balance: float
    released_balance: float
    refunded_balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: UUID
    transaction_type: str
    amount: float
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
