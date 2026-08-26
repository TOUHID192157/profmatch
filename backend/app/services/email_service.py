"""
Email service — drafts personalized outreach emails to matched
professors (via the unified LLM service, app.services.llm_service)
and sends them (via Resend).
"""

import json

import resend

from app.core.config import settings
from app.services.llm_service import call_llm, strip_json_fences, LLMUnavailableError

_resend_configured = False


def _ensure_resend_configured() -> None:
    global _resend_configured
    if not _resend_configured:
        if not settings.resend_api_key:
            raise RuntimeError("RESEND_API_KEY is not set. Add it to your .env file.")
        resend.api_key = settings.resend_api_key
        _resend_configured = True


async def draft_outreach_email(
    student_name: str,
    student_bio: str | None,
    student_research_interests: str | None,
    professor_name: str,
    professor_university: str,
    professor_research_areas: str,
) -> dict:
    """
    Use the unified LLM service to draft a personalized outreach email
    from a student to a matched professor. Returns
    {"subject": ..., "body": ...}. Falls back to a generic message if
    every LLM provider is unavailable, or if the LLM's response isn't
    usable JSON, rather than raising or crashing.
    """
    prompt = f"""Write a short, professional graduate school outreach email
from a prospective student to a professor, expressing genuine interest
in their research and asking about openings for graduate students.

STUDENT:
Name: {student_name}
Bio: {student_bio or "Not provided"}
Research interests: {student_research_interests or "Not provided"}

PROFESSOR:
Name: {professor_name}
University: {professor_university}
Research areas: {professor_research_areas}

Requirements:
- Reference the professor's actual research areas specifically, not generically.
- Keep the body under 200 words.
- Professional but warm tone, not overly formal or robotic.
- Do not invent specific facts about the student that weren't given above.
- Sign off with the student's name.

Respond with ONLY a JSON object with two keys: "subject" and "body".
No markdown fences, no other text.
"""

    fallback = {
        "subject": f"Interest in your research — {professor_name}",
        "body": "Unable to generate email body. Please write manually.",
    }

    try:
        text = strip_json_fences(await call_llm(prompt))
    except LLMUnavailableError as e:
        print(f"[email_service] draft generation failed, all providers exhausted: {e}")
        return fallback

    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("LLM returned valid JSON but not an object.")
        draft = parsed
    except (json.JSONDecodeError, ValueError):
        draft = {
            "subject": fallback["subject"],
            "body": text or fallback["body"],
        }

    return {
        "subject": draft.get("subject") or fallback["subject"],
        "body": draft.get("body") or fallback["body"],
    }


async def send_email(to_email: str, subject: str, body: str) -> dict:
    """Send an email via Resend."""
    _ensure_resend_configured()

    params = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    return resend.Emails.send(params)