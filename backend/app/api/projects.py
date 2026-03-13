from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.milestone import Milestone
from app.schemas.project import ProjectCreate, ProjectOut, ProjectAssign
from app.utils.security import get_current_user
from app.services.project_service import ProjectService
from app.ai.milestone_generator import MilestoneGenerator

router = APIRouter()


@router.post("/create", response_model=ProjectOut, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can create projects")

    service = ProjectService(db)
    generator = MilestoneGenerator()

    # AI generates milestones from description
    roadmap = await generator.generate(payload.description, payload.project_type)

    project_type = payload.project_type or ProjectType(roadmap.get("project_type", "other"))
    project = Project(
        title=payload.title,
        description=payload.description,
        project_type=project_type,
        total_budget=payload.total_budget,
        employer_id=current_user.id,
        ai_roadmap=roadmap,
    )
    db.add(project)
    await db.flush()

    # Create milestones from roadmap
    milestones_data = roadmap.get("milestones", [])
    total_milestones = len(milestones_data)
    for idx, m in enumerate(milestones_data):
        payment = round(payload.total_budget / total_milestones, 2) if total_milestones else 0
        milestone = Milestone(
            project_id=project.id,
            title=m["title"],
            description=m["description"],
            order_index=idx,
            deadline_days=m.get("deadline_days", 7),
            payment_amount=payment,
        )
        db.add(milestone)

    await db.commit()

    result = await db.execute(
        select(Project)
        .options(selectinload(Project.milestones))
        .where(Project.id == project.id)
    )
    return result.scalar_one()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.milestones))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/", response_model=list[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "employer":
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.milestones))
            .where(Project.employer_id == current_user.id)
        )
    else:
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.milestones))
            .where(
                (Project.freelancer_id == current_user.id) |
                (Project.status == ProjectStatus.active)
            )
        )
    return result.scalars().all()


@router.post("/{project_id}/assign", response_model=ProjectOut)
async def assign_freelancer(
    project_id: uuid.UUID,
    payload: ProjectAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).options(selectinload(Project.milestones)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")

    project.freelancer_id = payload.freelancer_id
    project.status = ProjectStatus.in_progress
    await db.commit()
    await db.refresh(project)
    return project
