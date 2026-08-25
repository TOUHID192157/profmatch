"""
Email service — drafts personalized outreach emails to matched
professors (via Gemini) and sends them (via Resend).
"""

import json

import resend
import asyncio
from google import genai

from app.core.config import settings
from app.core.key_rotation import get_next_gemini_key

_resend_configured = False


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using the next key in rotation."""
    return genai.Client(api_key=get_next_gemini_key())


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
    Use Gemini to draft a personalized outreach email from a student to
    a matched professor. Returns {"subject": ..., "body": ...}.
    """
    client = get_gemini_client()

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

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model="gemini-flash-latest",
                contents=prompt,
            ),
            timeout=30,
        )
    except asyncio.TimeoutError:
        print("[email_service] draft_outreach_email timed out after 30s")
        draft = {
            "subject": f"Interest in your research — {professor_name}",
            "body": "Unable to generate email body (service timed out). Please write manually.",
        }
        return {"subject": draft["subject"], "body": draft["body"]}

    

    text = (response.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        draft = json.loads(text)
    except json.JSONDecodeError:
        draft = {
            "subject": f"Interest in your research — {professor_name}",
            "body": text or "Unable to generate email body. Please write manually.",
        }

    return {
        "subject": draft.get("subject", f"Interest in your research — {professor_name}"),
        "body": draft.get("body", ""),
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