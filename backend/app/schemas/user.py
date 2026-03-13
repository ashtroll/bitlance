from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    employer = "employer"
    freelancer = "freelancer"
    admin = "admin"


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None
    role: UserRole


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
