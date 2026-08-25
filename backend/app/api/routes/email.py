import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.db.vector_store import supabase
from app.models.models import EmailDraft, StudentProfile, User
from app.schemas.schemas import EmailDraftOut
from app.services.email_service import draft_outreach_email, send_email

router = APIRouter(prefix="/api/email", tags=["email"])


class DraftEmailRequest(BaseModel):
    professor_id: uuid.UUID


class SendEmailRequest(BaseModel):
    draft_id: uuid.UUID


@router.post("/draft", response_model=EmailDraftOut)
async def create_email_draft(
    request: DraftEmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate a personalized outreach email draft for a matched
    professor. Looks up the professor's info from Supabase by id, and
    uses the student's saved profile for context — the frontend only
    needs to send professor_id.
    """
    professor_response = (
        supabase.table("professor_results")
        .select("name, university, email, research_areas")
        .eq("id", str(request.professor_id))
        .eq("user_id", str(current_user.id))
        .execute()
    )

    if not professor_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professor not found. Run a search first.",
        )

    professor = professor_response.data[0]

    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    draft = await draft_outreach_email(
        student_name=current_user.full_name,
        student_bio=profile.bio if profile else None,
        student_research_interests=profile.research_interests if profile else None,
        professor_name=professor.get("name", ""),
        professor_university=professor.get("university", ""),
        professor_research_areas=professor.get("research_areas", ""),
    )

    email_draft = EmailDraft(
        user_id=current_user.id,
        professor_name=professor.get("name", ""),
        professor_email=professor.get("email") or None,
        subject=draft["subject"],
        body=draft["body"],
        status="draft",
    )
    db.add(email_draft)
    db.commit()
    db.refresh(email_draft)

    return email_draft


@router.get("/drafts", response_model=list[EmailDraftOut])
def list_my_drafts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all email drafts/sent emails for the current student."""
    return (
        db.query(EmailDraft)
        .filter(EmailDraft.user_id == current_user.id)
        .order_by(EmailDraft.created_at.desc())
        .all()
    )


@router.post("/send", response_model=EmailDraftOut)
async def send_email_draft(
    request: SendEmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send a previously created email draft via Resend."""
    draft = (
        db.query(EmailDraft)
        .filter(
            EmailDraft.id == request.draft_id,
            EmailDraft.user_id == current_user.id,
        )
        .first()
    )

    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found.")

    if not draft.professor_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This draft has no professor email address to send to.",
        )

    try:
        await send_email(draft.professor_email, draft.subject, draft.body)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    draft.status = "sent"
    draft.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)

    return draft