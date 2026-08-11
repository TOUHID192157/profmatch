from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models.models import StudentProfile, User
from app.schemas.schemas import ProfessorResultOut
from app.services.search_service import find_matching_professors

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
        # Raised by embedding/search services when an API key is missing
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return matches