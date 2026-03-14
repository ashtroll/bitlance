from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date, timedelta
import uuid

from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.milestone import Milestone
from app.schemas.project import ProjectCreate, ProjectOut, ProjectAssign, ProjectUpdate
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
    roadmap = await generator.generate(
        payload.description,
        payload.project_type,
        budget=payload.total_budget,
        tech_stack=payload.tech_stack,
        language_preferences=payload.language_preferences,
        system_requirements=payload.system_requirements,
        special_notes=payload.special_notes,
    )

    project_type = payload.project_type or ProjectType(roadmap.get("project_type", "other"))
    roadmap["employer_specs"] = {
        "tech_stack": payload.tech_stack,
        "language_preferences": payload.language_preferences,
        "system_requirements": payload.system_requirements,
        "special_notes": payload.special_notes,
    }

    project = Project(
        title=payload.title,
        description=payload.description,
        project_type=project_type,
        status=ProjectStatus.active,
        total_budget=payload.total_budget,
        employer_id=current_user.id,
        ai_roadmap=roadmap,
    )
    db.add(project)
    await db.flush()

    # Create milestones from roadmap
    milestones_data = roadmap.get("milestones", [])
    total_milestones = len(milestones_data)
    cumulative_days = 0
    for idx, m in enumerate(milestones_data):
        weight = m.get("budget_weight", 1.0 / total_milestones if total_milestones else 1.0)
        payment = round(payload.total_budget * weight, 2)
        deadline_days = m.get("deadline_days", 7)
        cumulative_days += deadline_days
        milestone = Milestone(
            project_id=project.id,
            title=m["title"],
            description=m["description"],
            order_index=idx,
            deadline_days=deadline_days,
            due_date=date.today() + timedelta(days=cumulative_days),
            acceptance_criteria=m.get("acceptance_criteria", []),
            deliverable_type=m.get("deliverable_type", "code"),
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
                (Project.status.in_([ProjectStatus.active, ProjectStatus.draft]))
            )
        )
    return result.scalars().all()


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
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
    if project.status not in (ProjectStatus.draft, ProjectStatus.active):
        raise HTTPException(status_code=400, detail="Only draft or active projects can be edited")

    if payload.title is not None:
        project.title = payload.title
    if payload.description is not None:
        project.description = payload.description
    if payload.total_budget is not None:
        project.total_budget = payload.total_budget

    await db.commit()
    result = await db.execute(
        select(Project).options(selectinload(Project.milestones)).where(Project.id == project_id)
    )
    return result.scalar_one()


@router.patch("/{project_id}/cancel", response_model=ProjectOut)
async def cancel_project(
    project_id: uuid.UUID,
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
    if project.status in (ProjectStatus.completed, ProjectStatus.cancelled):
        raise HTTPException(status_code=400, detail=f"Project is already {project.status}")
    if project.status == ProjectStatus.in_progress:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a project that is in progress. Raise a dispute instead."
        )

    project.status = ProjectStatus.cancelled
    await db.commit()
    await db.refresh(project)

    result = await db.execute(
        select(Project).options(selectinload(Project.milestones)).where(Project.id == project_id)
    )
    return result.scalar_one()


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.transaction import EscrowAccount
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.milestones), selectinload(Project.escrow))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    if project.status not in (ProjectStatus.draft, ProjectStatus.active, ProjectStatus.cancelled):
        raise HTTPException(
            status_code=400,
            detail="Only draft, active, or cancelled projects can be deleted"
        )

    await db.delete(project)
    await db.commit()


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


@router.post("/{project_id}/milestones/{milestone_id}/assign-freelancer", response_model=ProjectOut)
async def assign_freelancer_to_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
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

    m_result = await db.execute(
        select(Milestone).where(Milestone.id == milestone_id, Milestone.project_id == project_id)
    )
    milestone = m_result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone.assigned_freelancer_id = payload.freelancer_id
    await db.commit()

    result = await db.execute(
        select(Project).options(selectinload(Project.milestones)).where(Project.id == project_id)
    )
    return result.scalar_one()
