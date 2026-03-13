from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.reputation import ReputationScore
from app.schemas.user import UserRegister, UserLogin, UserOut, TokenResponse
from app.utils.security import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check duplicates
    existing = await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already registered")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()

    # Initialize reputation score for freelancers
    if payload.role == "freelancer":
        rep = ReputationScore(user_id=user.id)
        db.add(rep)

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(__import__('app.utils.security', fromlist=['get_current_user']).get_current_user)):
    return current_user
