from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User
from app.models.reputation import ReputationScore
from app.schemas.reputation import ReputationOut
from app.utils.security import get_current_user

router = APIRouter()


@router.get("/{freelancer_id}", response_model=ReputationOut)
async def get_reputation(
    freelancer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReputationScore).where(ReputationScore.user_id == freelancer_id)
    )
    rep = result.scalar_one_or_none()
    if not rep:
        raise HTTPException(status_code=404, detail="Reputation score not found")
    return rep


@router.get("/me/score", response_model=ReputationOut)
async def my_reputation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReputationScore).where(ReputationScore.user_id == current_user.id)
    )
    rep = result.scalar_one_or_none()
    if not rep:
        raise HTTPException(status_code=404, detail="No reputation score yet")
    return rep
