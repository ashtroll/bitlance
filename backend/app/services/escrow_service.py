import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.transaction import EscrowAccount, Transaction, TransactionType, TransactionStatus
from app.models.milestone import Milestone
from app.config import settings


class EscrowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def deposit(self, project_id: uuid.UUID, user_id: uuid.UUID, amount: float) -> EscrowAccount:
        """Deposit funds into a project escrow account."""
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Deposit amount must be positive")

        # Get or create escrow account
        result = await self.db.execute(
            select(EscrowAccount).where(EscrowAccount.project_id == project_id)
        )
        escrow = result.scalar_one_or_none()

        if not escrow:
            escrow = EscrowAccount(project_id=project_id, user_id=user_id)
            self.db.add(escrow)
            await self.db.flush()

        escrow.total_deposited += amount

        # Lock funds per milestone proportionally
        await self._lock_milestone_funds(escrow, project_id, amount)

        # Record transaction
        tx = Transaction(
            escrow_account_id=escrow.id,
            transaction_type=TransactionType.deposit,
            amount=amount,
            status=TransactionStatus.completed,
            notes=f"Employer deposit of ${amount:.2f}",
        )
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(escrow)
        return escrow

    async def _lock_milestone_funds(self, escrow: EscrowAccount, project_id: uuid.UUID, amount: float):
        """Distribute deposited funds across pending milestones."""
        result = await self.db.execute(
            select(Milestone).where(
                Milestone.project_id == project_id,
                Milestone.release_status == "locked",
            )
        )
        milestones = result.scalars().all()
        if not milestones:
            return

        per_milestone = amount / len(milestones)
        for m in milestones:
            m.locked_amount += per_milestone
            escrow.locked_balance += per_milestone

        # Record lock transactions
        for m in milestones:
            tx = Transaction(
                escrow_account_id=escrow.id,
                milestone_id=m.id,
                transaction_type=TransactionType.lock,
                amount=per_milestone,
                status=TransactionStatus.completed,
                notes=f"Funds locked for milestone: {m.title}",
            )
            self.db.add(tx)

    async def release_payment(self, milestone_id: uuid.UUID, project_id: uuid.UUID) -> Transaction:
        """Release escrow funds to freelancer upon milestone approval."""
        result = await self.db.execute(select(Milestone).where(Milestone.id == milestone_id))
        milestone = result.scalar_one_or_none()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        if milestone.release_status == "released":
            raise HTTPException(status_code=400, detail="Payment already released for this milestone")

        escrow_result = await self.db.execute(
            select(EscrowAccount).where(EscrowAccount.project_id == project_id)
        )
        escrow = escrow_result.scalar_one_or_none()
        if not escrow:
            # No escrow — mark milestone as released without monetary action
            milestone.release_status = "released"
            milestone.payment_timestamp = datetime.utcnow()
            return None

        amount = milestone.locked_amount
        if amount <= 0:
            # No funds locked — still mark released
            milestone.release_status = "released"
            milestone.payment_timestamp = datetime.utcnow()
            return None

        # Calculate platform fee
        fee = round(amount * (settings.platform_fee_percent / 100), 2)
        freelancer_amount = round(amount - fee, 2)

        # Update escrow balances
        escrow.locked_balance = max(0, escrow.locked_balance - amount)
        escrow.released_balance += freelancer_amount

        # Update milestone
        milestone.release_status = "released"
        milestone.payment_timestamp = datetime.utcnow()

        # Record release transaction
        tx = Transaction(
            escrow_account_id=escrow.id,
            milestone_id=milestone_id,
            transaction_type=TransactionType.release,
            amount=freelancer_amount,
            status=TransactionStatus.completed,
            notes=f"Payment released. Platform fee: ${fee:.2f}",
        )
        self.db.add(tx)

        # Record fee transaction
        fee_tx = Transaction(
            escrow_account_id=escrow.id,
            milestone_id=milestone_id,
            transaction_type=TransactionType.platform_fee,
            amount=fee,
            status=TransactionStatus.completed,
            notes=f"Platform fee ({settings.platform_fee_percent}%)",
        )
        self.db.add(fee_tx)

        await self.db.flush()
        return tx

    async def refund(self, milestone_id: uuid.UUID, project_id: uuid.UUID, percent: float = 100.0) -> Transaction:
        """Refund locked milestone funds to employer."""
        result = await self.db.execute(select(Milestone).where(Milestone.id == milestone_id))
        milestone = result.scalar_one_or_none()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        escrow_result = await self.db.execute(
            select(EscrowAccount).where(EscrowAccount.project_id == project_id)
        )
        escrow = escrow_result.scalar_one_or_none()
        if not escrow:
            milestone.release_status = "refunded"
            return None

        refund_amount = round(milestone.locked_amount * (percent / 100), 2)
        escrow.locked_balance = max(0, escrow.locked_balance - refund_amount)
        escrow.refunded_balance += refund_amount
        milestone.release_status = "refunded"

        tx = Transaction(
            escrow_account_id=escrow.id,
            milestone_id=milestone_id,
            transaction_type=TransactionType.refund,
            amount=refund_amount,
            status=TransactionStatus.completed,
            notes=f"Refund of {percent}% to employer",
        )
        self.db.add(tx)
        await self.db.flush()
        return tx
