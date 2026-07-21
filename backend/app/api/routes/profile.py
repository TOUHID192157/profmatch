from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models.models import StudentProfile, User
from app.schemas.schemas import StudentProfileCreate, StudentProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("", response_model=StudentProfileOut, status_code=status.HTTP_201_CREATED)
def create_or_update_profile(
    profile_in: StudentProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create the student's profile if it doesn't exist yet, or update it
    if it already does (upsert behavior).
    """
    existing_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if existing_profile:
        for field, value in profile_in.model_dump(exclude_unset=True).items():
            setattr(existing_profile, field, value)
        db.commit()
        db.refresh(existing_profile)
        return existing_profile

    new_profile = StudentProfile(
        user_id=current_user.id,
        **profile_in.model_dump(),
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile


@router.get("", response_model=StudentProfileOut)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get the currently logged-in student's profile."""
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one first with POST /api/profile.",
        )
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete the currently logged-in student's profile."""
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    db.delete(profile)
    db.commit()
    return None