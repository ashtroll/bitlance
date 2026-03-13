from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.transaction import EscrowAccount, Transaction, TransactionType, TransactionStatus
from app.schemas.payment import DepositRequest, ReleaseRequest, EscrowOut, TransactionOut
from app.utils.security import get_current_user
from app.services.escrow_service import EscrowService

router = APIRouter()


@router.post("/deposit", response_model=EscrowOut)
async def deposit_funds(
    payload: DepositRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can deposit funds")

    result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = result.scalar_one_or_none()
    if not project or project.employer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    escrow_svc = EscrowService(db)
    escrow = await escrow_svc.deposit(
        project_id=payload.project_id,
        user_id=current_user.id,
        amount=payload.amount,
    )
    return escrow


@router.post("/release", response_model=TransactionOut)
async def release_payment(
    payload: ReleaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("employer", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    from app.models.milestone import Milestone
    result = await db.execute(select(Milestone).where(Milestone.id == payload.milestone_id))
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    escrow_svc = EscrowService(db)
    tx = await escrow_svc.release_payment(payload.milestone_id, milestone.project_id)
    return tx


@router.get("/escrow/{project_id}", response_model=EscrowOut)
async def get_escrow(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EscrowAccount).where(EscrowAccount.project_id == project_id)
    )
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=404, detail="No escrow account for this project")
    return escrow


@router.get("/transactions/{project_id}", response_model=list[TransactionOut])
async def get_transactions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EscrowAccount).where(EscrowAccount.project_id == project_id)
    )
    escrow = result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=404, detail="No escrow for this project")

    tx_result = await db.execute(
        select(Transaction).where(Transaction.escrow_account_id == escrow.id)
    )
    return tx_result.scalars().all()
