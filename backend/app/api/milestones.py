from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.database import get_db
from app.models.user import User
from app.models.milestone import Milestone, MilestoneStatus
from app.models.submission import Submission
from app.schemas.milestone import MilestoneSubmit, SubmissionOut, MilestoneEvaluateRequest, EvaluationOut
from app.utils.security import get_current_user
from app.ai.qa_engine import QAEngine
from app.services.escrow_service import EscrowService
from app.services.pfi_service import PFIService

router = APIRouter()


@router.post("/submit", response_model=SubmissionOut, status_code=201)
async def submit_milestone(
    payload: MilestoneSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "freelancer":
        raise HTTPException(status_code=403, detail="Only freelancers can submit milestones")

    result = await db.execute(
        select(Milestone).options(selectinload(Milestone.project)).where(Milestone.id == payload.milestone_id)
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    if milestone.project.freelancer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this project")

    submission = Submission(
        milestone_id=payload.milestone_id,
        freelancer_id=current_user.id,
        submission_type=payload.submission_type,
        content=payload.content,
        repo_url=payload.repo_url,
        notes=payload.notes,
    )
    db.add(submission)
    milestone.status = MilestoneStatus.submitted
    await db.commit()
    await db.refresh(submission)
    return submission


@router.post("/evaluate", response_model=EvaluationOut)
async def evaluate_milestone(
    payload: MilestoneEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.milestone).selectinload(Milestone.project))
        .where(Submission.id == payload.submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    milestone = submission.milestone
    project = milestone.project

    # Employer or admin can trigger evaluation
    if current_user.role == "freelancer":
        raise HTTPException(status_code=403, detail="Freelancers cannot trigger evaluation")

    qa = QAEngine()
    evaluation = await qa.evaluate(submission, milestone, project, db)

    # Auto-release payment if confident and complete
    if evaluation.completion_status == "complete" and evaluation.confidence_score >= 0.80:
        escrow_svc = EscrowService(db)
        await escrow_svc.release_payment(milestone.id, project.id)
        milestone.status = MilestoneStatus.paid
        evaluation.auto_approved = True

        # Update PFI
        pfi_svc = PFIService(db)
        await pfi_svc.update_score(
            freelancer_id=submission.freelancer_id,
            milestone_success=True,
            quality_score=evaluation.quality_score or evaluation.confidence_score,
            on_time=True,
            disputed=False,
        )
    elif evaluation.completion_status == "failed":
        milestone.status = MilestoneStatus.rejected
        pfi_svc = PFIService(db)
        await pfi_svc.update_score(
            freelancer_id=submission.freelancer_id,
            milestone_success=False,
            quality_score=evaluation.quality_score or 0.0,
            on_time=False,
            disputed=False,
        )
    else:
        milestone.status = MilestoneStatus.under_review

    await db.commit()
    await db.refresh(evaluation)
    return evaluation
