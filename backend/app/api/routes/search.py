from pydantic import BaseModel
from app.agents.orchestrator import run_orchestrator

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.db.vector_store import supabase
from app.models.models import StudentProfile, User
from app.schemas.schemas import ProfessorResultOut
from app.services.search_service import find_matching_professors, find_missing_email
from app.mcp_servers.mcp_client import run_agentic_search_sync

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/matches", response_model=list[ProfessorResultOut])
async def get_matches(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Find professors matching the current student's profile.

    Reads the student's saved profile, searches the web for relevant
    professors, embeds and ranks them, and returns the top matches.
    """
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Please complete your profile before searching for matches.",
        )

    if not profile.research_interests and not profile.bio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add research interests or a bio to your profile first.",
        )

    try:
        matches = await find_matching_professors(
            user_id=str(current_user.id),
            research_interests=profile.research_interests,
            bio=profile.bio,
            skills=profile.skills,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Our AI service is temporarily busy. Please wait about a minute and try again.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong during matching.",
        )

    return matches


@router.post("/professors/{professor_id}/find-email", response_model=ProfessorResultOut)
async def find_professor_email(
    professor_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
):
    """
    On-demand: try to find a missing email address for one specific
    professor the student already matched with. Triggered by the user
    clicking "Find Email" on a single professor card, so we only make
    the extra API calls when actually needed.
    """
    professor_response = (
        supabase.table("professor_results")
        .select("*")
        .eq("id", str(professor_id))
        .eq("user_id", str(current_user.id))
        .execute()
    )

    if not professor_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Professor not found."
        )

    professor = professor_response.data[0]

    if professor.get("email"):
        return professor

    try:
        email = await find_missing_email(
            professor.get("name", ""), professor.get("university", "")
        )
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Our AI service is temporarily busy. Please wait a bit and try again.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email search failed.",
        )

    if email:
        supabase.table("professor_results").update({"email": email}).eq(
            "id", str(professor_id)
        ).execute()
        professor["email"] = email

    return professor


@router.post("/matches-agentic")
async def get_matches_agentic(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Experimental: same goal as /matches, but Gemini decides which
    tools (search, email lookup) to call via the MCP server, instead
    of a fixed pipeline. Runs in a separate thread with its own event
    loop to work around a Windows-specific conflict between uvicorn's
    event loop and MCP's subprocess-based stdio transport.
    """
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if not profile or not (profile.research_interests or profile.bio):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your profile with research interests first.",
        )

    try:
        result = await asyncio.to_thread(
            run_agentic_search_sync, profile.research_interests or profile.bio
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agentic search failed: {e}",
        )

    return {"professors": result}

class OrchestrateRequest(BaseModel):
    authorize_send: bool = False


@router.post("/orchestrate")
async def orchestrate_matches(
    request: OrchestrateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if not profile or not (profile.research_interests or profile.bio):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your profile with research interests first.",
        )

    result = await run_orchestrator(
        student_name=current_user.full_name,
        student_bio=profile.bio,
        student_research_interests=profile.research_interests,
        authorize_send=request.authorize_send,
    )

    return result