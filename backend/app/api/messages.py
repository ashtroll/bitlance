from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
import uuid

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.message import Message
from app.utils.security import get_current_user

router = APIRouter()


class MessageCreate(BaseModel):
    content: str


class SenderOut(BaseModel):
    id: UUID
    username: str
    role: str
    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: UUID
    project_id: UUID
    sender_id: UUID
    content: str
    message_type: str
    created_at: datetime
    sender: SenderOut
    model_config = {"from_attributes": True}


@router.get("/{project_id}/messages", response_model=list[MessageOut])
async def get_messages(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify access
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role == "employer" and project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")

    msgs = await db.execute(
        select(Message)
        .options(selectinload(Message.sender))
        .where(Message.project_id == project_id)
        .order_by(Message.created_at.asc())
    )
    return msgs.scalars().all()


@router.post("/{project_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    project_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Allow: employer (owner) or assigned freelancer(s)
    if current_user.role == "employer" and project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")

    msg = Message(
        project_id=project_id,
        sender_id=current_user.id,
        content=payload.content.strip(),
        message_type="user",
    )
    db.add(msg)
    await db.commit()

    result = await db.execute(
        select(Message).options(selectinload(Message.sender)).where(Message.id == msg.id)
    )
    return result.scalar_one()
