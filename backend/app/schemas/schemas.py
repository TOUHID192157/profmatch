import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- USER / AUTH ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- STUDENT PROFILE ----------

class StudentProfileCreate(BaseModel):
    university: str | None = None
    degree: str | None = None
    major: str | None = None
    gpa: float | None = None
    graduation_year: int | None = None
    research_interests: str | None = None
    bio: str | None = None
    research_paper_links: list[str] | None = None
    skills: list[str] | None = None
    gre_score: int | None = None
    ielts_score: float | None = None


class StudentProfileOut(StudentProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID


# ---------- PROFESSOR RESULTS ----------

class ProfessorResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    university: str | None = None
    department: str | None = None
    email: str | None = None
    research_areas: str | None = None
    profile_url: str | None = None
    match_reason: str | None = None


# ---------- EMAIL DRAFTS ----------

class EmailDraftCreate(BaseModel):
    professor_name: str
    professor_email: str | None = None
    subject: str
    body: str


class EmailDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    professor_name: str
    professor_email: str | None = None
    subject: str
    body: str
    status: str
    sent_at: datetime | None = None
    created_at: datetime