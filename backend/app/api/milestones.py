from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.models.milestone import Milestone, MilestoneStatus
from app.models.submission import Submission
from app.models.evaluation import Evaluation
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
        select(Milestone)
        .options(selectinload(Milestone.project))
        .where(Milestone.id == payload.milestone_id)
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    is_project_freelancer = milestone.project.freelancer_id == current_user.id
    is_milestone_freelancer = milestone.assigned_freelancer_id == current_user.id
    if not (is_project_freelancer or is_milestone_freelancer):
        raise HTTPException(status_code=403, detail="You are not assigned to this project")
    if milestone.status == MilestoneStatus.paid:
        raise HTTPException(status_code=400, detail="Milestone already paid")

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

    # Auto-evaluate the submission
    try:
        from datetime import date as _date
        from app.ai.qa_engine import QAEngine
        from app.services.escrow_service import EscrowService
        from app.services.pfi_service import PFIService
        from app.models.evaluation import Evaluation, CompletionStatus

        project = milestone.project
        on_time = True
        if milestone.due_date:
            on_time = _date.today() <= milestone.due_date

        qa = QAEngine()
        evaluation = await qa.evaluate(submission, milestone, project, db)

        escrow_svc = EscrowService(db)
        pfi_svc = PFIService(db)

        if evaluation.completion_status == CompletionStatus.complete and evaluation.confidence_score >= 0.80:
            await escrow_svc.release_payment(milestone.id, project.id)
            milestone.status = MilestoneStatus.paid
            evaluation.auto_approved = True
            await pfi_svc.update_score(
                freelancer_id=submission.freelancer_id,
                milestone_success=True,
                quality_score=evaluation.quality_score or evaluation.confidence_score,
                on_time=on_time, disputed=False,
            )
        elif evaluation.completion_status == CompletionStatus.partial:
            payout_percent = round(evaluation.confidence_score * 100, 1)
            refund_percent = round(100 - payout_percent, 1)
            if refund_percent > 0:
                await escrow_svc.refund(milestone.id, project.id, percent=refund_percent)
            await escrow_svc.release_payment(milestone.id, project.id)
            milestone.status = MilestoneStatus.approved
            evaluation.auto_approved = True
            await pfi_svc.update_score(
                freelancer_id=submission.freelancer_id,
                milestone_success=False,
                quality_score=evaluation.quality_score or evaluation.confidence_score,
                on_time=on_time, disputed=False,
            )
        elif evaluation.completion_status == CompletionStatus.failed:
            await escrow_svc.refund(milestone.id, project.id, percent=100.0)
            milestone.status = MilestoneStatus.rejected
            await pfi_svc.update_score(
                freelancer_id=submission.freelancer_id,
                milestone_success=False,
                quality_score=evaluation.quality_score or 0.0,
                on_time=False, disputed=False,
            )
        else:
            milestone.status = MilestoneStatus.under_review

        await db.commit()

        # Post a system message to the discussion thread about evaluation result
        try:
            from app.models.message import Message
            status_text = {
                "complete": "✅ AI Evaluation: Milestone APPROVED — payment released automatically.",
                "partial": f"⚠️ AI Evaluation: Milestone PARTIALLY approved ({round(evaluation.confidence_score*100)}% quality). Pro-rated payment released.",
                "failed": "❌ AI Evaluation: Milestone REJECTED — full refund issued. Please review feedback and resubmit.",
            }.get(evaluation.completion_status.value, "🔍 AI Evaluation complete — manual review required.")

            feedback_msg = f"{status_text}\n\n**AI Feedback:** {evaluation.feedback or 'No detailed feedback available.'}"
            system_msg = Message(
                project_id=project.id,
                sender_id=submission.freelancer_id,
                content=feedback_msg,
                message_type="system",
            )
            db.add(system_msg)
            await db.commit()
        except Exception:
            pass  # Don't fail submission if message posting fails

    except Exception as auto_eval_err:
        import logging
        logging.getLogger("app").error(f"Auto-evaluation error for submission {submission.id}: {auto_eval_err}", exc_info=True)
        # Post error message to discussion so both parties know
        try:
            from app.models.message import Message
            project = milestone.project
            err_msg = Message(
                project_id=project.id,
                sender_id=submission.freelancer_id,
                content=f"⚠️ Auto-evaluation encountered an issue: {str(auto_eval_err)}\n\nThe submission has been saved. The employer can trigger a manual re-evaluation.",
                message_type="system",
            )
            db.add(err_msg)
        except Exception:
            pass
        milestone.status = MilestoneStatus.under_review
        await db.commit()

    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.evaluation))
        .where(Submission.id == submission.id)
    )
    return result.scalar_one()


@router.get("/{milestone_id}/submissions", response_model=list[SubmissionOut])
async def get_submissions(
    milestone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Milestone)
        .options(selectinload(Milestone.project))
        .where(Milestone.id == milestone_id)
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    project = milestone.project
    if current_user.role == "employer" and project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    if current_user.role == "freelancer":
        is_project_fl = project.freelancer_id == current_user.id
        is_milestone_fl = milestone.assigned_freelancer_id == current_user.id
        if not (is_project_fl or is_milestone_fl):
            raise HTTPException(status_code=403, detail="Not your project")

    subs = await db.execute(
        select(Submission)
        .options(selectinload(Submission.evaluation))
        .where(Submission.milestone_id == milestone_id)
        .order_by(Submission.created_at.desc())
    )
    return subs.scalars().all()


@router.post("/evaluate", response_model=EvaluationOut)
async def evaluate_milestone(
    payload: MilestoneEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "freelancer":
        raise HTTPException(status_code=403, detail="Freelancers cannot trigger evaluation")

    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.milestone).selectinload(Milestone.project)
        )
        .where(Submission.id == payload.submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    milestone = submission.milestone
    project = milestone.project

    if current_user.role == "employer" and project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")

    # Check if already evaluated
    existing_eval = await db.execute(
        select(Evaluation).where(Evaluation.submission_id == submission.id)
    )
    if existing_eval.scalar_one_or_none() and not payload.force:
        raise HTTPException(status_code=409, detail="Submission already evaluated. Use force=true to re-evaluate.")

    # Deadline adherence
    on_time = True
    if milestone.due_date:
        on_time = date.today() <= milestone.due_date

    qa = QAEngine()
    evaluation = await qa.evaluate(submission, milestone, project, db)

    escrow_svc = EscrowService(db)
    pfi_svc = PFIService(db)

    if evaluation.completion_status == "complete" and evaluation.confidence_score >= 0.80:
        await escrow_svc.release_payment(milestone.id, project.id)
        milestone.status = MilestoneStatus.paid
        evaluation.auto_approved = True
        await pfi_svc.update_score(
            freelancer_id=submission.freelancer_id,
            milestone_success=True,
            quality_score=evaluation.quality_score or evaluation.confidence_score,
            on_time=on_time,
            disputed=False,
        )

    elif evaluation.completion_status == "partial":
        payout_percent = round(evaluation.confidence_score * 100, 1)
        refund_percent = round(100 - payout_percent, 1)
        if refund_percent > 0:
            await escrow_svc.refund(milestone.id, project.id, percent=refund_percent)
        await escrow_svc.release_payment(milestone.id, project.id)
        milestone.status = MilestoneStatus.approved
        evaluation.auto_approved = True
        await pfi_svc.update_score(
            freelancer_id=submission.freelancer_id,
            milestone_success=False,
            quality_score=evaluation.quality_score or evaluation.confidence_score,
            on_time=on_time,
            disputed=False,
        )

    elif evaluation.completion_status == "failed":
        await escrow_svc.refund(milestone.id, project.id, percent=100.0)
        milestone.status = MilestoneStatus.rejected
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


@router.post("/dispute")
async def raise_dispute(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Raise a dispute on a milestone and get instant AI arbitration."""
    import json as _json
    import re as _re
    from app.ai.prompts import DISPUTE_ANALYSIS_PROMPT
    from app.ai.qa_engine import QAEngine
    from app.models.message import Message
    from app.config import settings as _settings

    submission_id = payload.get("submission_id")
    concern = payload.get("concern", "").strip()
    if not submission_id or not concern:
        raise HTTPException(status_code=400, detail="submission_id and concern are required")

    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.milestone).selectinload(Milestone.project))
        .where(Submission.id == uuid.UUID(str(submission_id)))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    milestone = submission.milestone
    project = milestone.project

    if current_user.role == "employer" and project.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    if current_user.role == "freelancer" and submission.freelancer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")

    eval_result = await db.execute(
        select(Evaluation).where(Evaluation.submission_id == submission.id)
    )
    evaluation = eval_result.scalar_one_or_none()

    qa = QAEngine()
    try:
        client = qa._get_client()
        prompt = DISPUTE_ANALYSIS_PROMPT.format(
            project_title=project.title,
            milestone_title=milestone.title,
            milestone_description=milestone.description,
            acceptance_criteria=_json.dumps(milestone.acceptance_criteria or []),
            submission_content=submission.content or "See repo URL",
            repo_url=submission.repo_url or "N/A",
            ai_evaluation=_json.dumps(evaluation.llm_review if evaluation else {}),
            employer_concern=concern,
        )
        response = await client.chat.completions.create(
            model=_settings.ai_model,
            messages=[
                {"role": "system", "content": "You are a neutral arbitrator. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        raw = _re.sub(r"```json\s*|\s*```", "", response.choices[0].message.content).strip()
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        arbitration = _json.loads(m.group(0) if m else raw)
    except Exception as e:
        arbitration = {
            "recommended_resolution": "mediation_required",
            "reasoning": f"AI arbitration unavailable: {str(e)[:100]}. Human review required.",
            "suggested_payout_percent": 50,
            "confidence": 0.0,
        }

    resolution = arbitration.get("recommended_resolution", "pending").replace("_", " ").title()
    payout = arbitration.get("suggested_payout_percent", 50)
    reasoning = arbitration.get("reasoning", "N/A")

    msg = Message(
        project_id=project.id,
        sender_id=current_user.id,
        content=(
            f"⚖️ **Dispute raised by {current_user.username}**\n\n"
            f"**Concern:** {concern}\n\n"
            f"**AI Arbitration:** {resolution}\n"
            f"**Suggested Payout:** {payout}%\n\n"
            f"**Reasoning:** {reasoning}"
        ),
        message_type="system",
    )
    db.add(msg)
    milestone.status = MilestoneStatus.under_review
    await db.commit()

    return {"arbitration": arbitration, "milestone_id": str(milestone.id)}
