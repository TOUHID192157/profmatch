"""
Email Agent — owns email drafting and sending only. Wraps the
existing email_service (draft_outreach_email, send_email) and adds
its own Gemini call with a review-focused system prompt: it judges
whether a draft is personalized/appropriate enough to send.
"""

import json

from google import genai
from google.genai import types as genai_types

from app.core.key_rotation import get_next_gemini_key
from app.services.email_service import draft_outreach_email, send_email

_SYSTEM_PROMPT = """You are the Email Agent in a multi-agent system.

Your ONLY job is to review a drafted outreach email and judge whether
it is genuinely personalized to the professor's research (not generic),
professional, and under 200 words.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"approved": true}
or
{"approved": false, "reason": "..."}
"""


async def _review_draft(subject: str, body: str, professor: dict) -> dict:
    client = genai.Client(api_key=get_next_gemini_key())

    prompt = f"""PROFESSOR: {professor.get('name')} — {professor.get('research_area', professor.get('research_areas', ''))}

DRAFT SUBJECT: {subject}

DRAFT BODY:
{body}
"""

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=genai_types.GenerateContentConfig(system_instruction=_SYSTEM_PROMPT),
    )

    text = (response.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"approved": True}


async def run_email_agent(
    student_name: str,
    student_bio: str | None,
    student_research_interests: str | None,
    professor: dict,
    authorize_send: bool = False,
) -> dict:
    professor_name = professor.get("name", "Unknown")
    professor_email = professor.get("email")

    print(f"[EmailAgent] drafting for {professor_name}")

    try:
        draft = await draft_outreach_email(
            student_name=student_name,
            student_bio=student_bio,
            student_research_interests=student_research_interests,
            professor_name=professor_name,
            professor_university=professor.get("university", ""),
            professor_research_areas=professor.get("research_area")
            or professor.get("research_areas", ""),
        )
    except Exception as e:
        print(f"[EmailAgent] draft generation failed: {e}")
        return {
            "status": "failed",
            "recipient": professor_email or "",
            "error": f"Draft generation failed: {e}",
        }

    subject, body = draft["subject"], draft["body"]

    try:
        review = await _review_draft(subject, body, professor)
    except Exception as e:
        print(f"[EmailAgent] review step failed, proceeding anyway: {e}")
        review = {"approved": True}

    if not review.get("approved", True):
        print(f"[EmailAgent] draft not approved: {review.get('reason')}")
        try:
            draft = await draft_outreach_email(
                student_name=student_name,
                student_bio=student_bio,
                student_research_interests=student_research_interests,
                professor_name=professor_name,
                professor_university=professor.get("university", ""),
                professor_research_areas=professor.get("research_area")
                or professor.get("research_areas", ""),
            )
            subject, body = draft["subject"], draft["body"]
        except Exception as e:
            return {
                "status": "failed",
                "recipient": professor_email or "",
                "error": f"Regeneration failed: {e}",
            }

    if not professor_email:
        print(f"[EmailAgent] no email address for {professor_name}, leaving as draft-only")
        return {
            "status": "drafted",
            "recipient": "",
            "subject": subject,
            "message": body,
        }

    if not authorize_send:
        print(f"[EmailAgent] drafted for {professor_name}, awaiting human approval to send")
        return {
            "status": "drafted",
            "recipient": professor_email,
            "subject": subject,
            "message": body,
        }

    try:
        await send_email(professor_email, subject, body)
        print(f"[EmailAgent] sent to {professor_email}")
        return {
            "status": "sent",
            "recipient": professor_email,
            "subject": subject,
            "message": body,
        }
    except Exception as e:
        print(f"[EmailAgent] send failed: {e}")
        return {
            "status": "failed",
            "recipient": professor_email,
            "error": str(e),
        }