import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.application import Application, ApplicationStatus
from app.models.milestone import Milestone
from app.schemas.application import ApplicationCreate, ApplicationReview, ApplicationOut
from app.utils.security import get_current_user

router = APIRouter()


@router.post("/{project_id}/apply", response_model=ApplicationOut, status_code=201)
async def apply_to_project(
    project_id: uuid.UUID,
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "freelancer":
        raise HTTPException(status_code=403, detail="Only freelancers can apply to projects")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in (ProjectStatus.active, ProjectStatus.draft):
        raise HTTPException(status_code=400, detail="Project is not accepting applications")
    if project.freelancer_id:
        raise HTTPException(status_code=400, detail="Project already has a freelancer assigned")

    # Check if already applied
    existing = await db.execute(
        select(Application).where(
            and_(
                Application.project_id == project_id,
                Application.freelancer_id == current_user.id,
                Application.status == ApplicationStatus.pending,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already applied to this project")

    application = Application(
        project_id=project_id,
        freelancer_id=current_user.id,
        cover_letter=payload.cover_letter,
        proposed_rate=payload.proposed_rate,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.freelancer))
        .where(Application.id == application.id)
    )
    return result.scalar_one()


@router.get("/{project_id}/applications", response_model=list[ApplicationOut])
async def list_applications(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == "employer" and project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    if current_user.role == "freelancer":
        raise HTTPException(status_code=403, detail="Freelancers cannot view all applications")

    apps = await db.execute(
        select(Application)
        .options(selectinload(Application.freelancer))
        .where(Application.project_id == project_id)
        .order_by(Application.created_at.desc())
    )
    return apps.scalars().all()


@router.post("/{project_id}/applications/{application_id}/review", response_model=ApplicationOut)
async def review_application(
    project_id: uuid.UUID,
    application_id: uuid.UUID,
    payload: ApplicationReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can review applications")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")

    app_result = await db.execute(
        select(Application)
        .options(selectinload(Application.freelancer))
        .where(and_(Application.id == application_id, Application.project_id == project_id))
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != ApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="Application already reviewed")

    application.status = payload.status
    application.employer_note = payload.employer_note

    if payload.status == ApplicationStatus.accepted:
        if project.freelancer_id:
            raise HTTPException(status_code=400, detail="Project already has a freelancer")

        # Assign freelancer to project
        project.freelancer_id = application.freelancer_id
        project.status = ProjectStatus.in_progress

        # Set milestones to in_progress
        milestones = await db.execute(
            select(Milestone).where(Milestone.project_id == project_id)
        )
        for m in milestones.scalars().all():
            m.status = "in_progress"

        # Reject all other pending applications
        other_apps = await db.execute(
            select(Application).where(
                and_(
                    Application.project_id == project_id,
                    Application.id != application_id,
                    Application.status == ApplicationStatus.pending,
                )
            )
        )
        for other in other_apps.scalars().all():
            other.status = ApplicationStatus.rejected
            other.employer_note = "Another freelancer was selected for this project."

    await db.commit()
    await db.refresh(application)
    return application


@router.delete("/{project_id}/apply", status_code=204)
async def withdraw_application(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "freelancer":
        raise HTTPException(status_code=403, detail="Only freelancers can withdraw applications")

    result = await db.execute(
        select(Application).where(
            and_(
                Application.project_id == project_id,
                Application.freelancer_id == current_user.id,
                Application.status == ApplicationStatus.pending,
            )
        )
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="No pending application found")

    application.status = ApplicationStatus.withdrawn
    await db.commit()
