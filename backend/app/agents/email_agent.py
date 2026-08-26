"""
Email Agent — drafts, reviews, and (optionally) sends an outreach
email for one matched professor. Owns no LLM provider logic itself —
all LLM calls go through app.services.llm_service.call_llm(), which
handles Gemini key rotation and gorouter.app fallback.

Does not do research or call MCP tools — receives professor data from
the Orchestrator and only processes it.
"""

import json

from app.services.email_service import draft_outreach_email, send_email
from app.services.llm_service import call_llm, strip_json_fences, LLMUnavailableError

_REVIEW_SYSTEM_PROMPT = """You are reviewing a drafted outreach email
for quality before it is shown to a student for approval.

Approve it only if it is genuinely personalized to the professor's
actual research (not generic), professional in tone, and does not
invent facts about the student that weren't provided.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"approved": true, "reason": "..."}
or
{"approved": false, "reason": "..."}
"""


def _empty_result(professor: dict) -> dict:
    """Base shape every code path fills in and returns, for a
    predictable structure regardless of outcome."""
    return {
        "status": "error",
        "professor": {
            "name": professor.get("name", "Unknown"),
            "email": professor.get("email") or None,
        },
        "email": None,
        "review": None,
        "error": None,
    }


async def _review_draft(subject: str, body: str, professor: dict) -> dict:
    """
    Ask the LLM whether a draft is good enough to send. Returns
    {"approved": bool, "reason": str}. On any failure to get a usable
    verdict, treats the draft as needing human review rather than
    silently approving or crashing.
    """
    prompt = f"""PROFESSOR: {professor.get('name')} — {professor.get('research_area', professor.get('research_areas', ''))}

DRAFT SUBJECT: {subject}

DRAFT BODY:
{body}
"""
    try:
        text = strip_json_fences(await call_llm(_REVIEW_SYSTEM_PROMPT + "\n\n" + prompt))
    except LLMUnavailableError:
        return {"approved": None, "reason": "Review LLM unavailable."}

    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict) or "approved" not in parsed:
            raise ValueError("Malformed review response.")
        return {
            "approved": parsed.get("approved"),
            "reason": parsed.get("reason", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {"approved": None, "reason": "Could not parse review response."}


async def run_email_agent(
    student_name: str,
    student_bio: str | None,
    student_research_interests: str | None,
    professor: dict,
    authorize_send: bool = False,
) -> dict:
    """
    Full per-professor flow: draft -> review -> (regenerate once if
    rejected) -> optionally send if authorized and an email exists.

    Always returns the same shape (see _empty_result), with `status`
    one of: "sent", "drafted", "needs_review", "send_failed", "error".
    """
    result = _empty_result(professor)
    professor_name = professor.get("name", "Unknown")
    professor_email = professor.get("email")

    print(f"[EmailAgent] drafting for {professor_name}")

    # ---- Draft ----
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
        print(f"[EmailAgent] draft generation raised unexpectedly: {e}")
        result["status"] = "error"
        result["error"] = f"Draft generation failed: {e}"
        return result

    subject, body = draft["subject"], draft["body"]

    # ---- Review ----
    review = await _review_draft(subject, body, professor)

    if review["approved"] is False:
        print(f"[EmailAgent] draft rejected: {review['reason']} — regenerating once")
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
            print(f"[EmailAgent] regeneration failed: {e}")
            result["status"] = "error"
            result["error"] = f"Regeneration failed: {e}"
            return result

        review = await _review_draft(subject, body, professor)
        if review["approved"] is False:
            print("[EmailAgent] second draft also rejected — flagging for human review")
            result["status"] = "needs_review"
            result["email"] = {"subject": subject, "body": body}
            result["review"] = review
            return result

    if review["approved"] is None:
        print("[EmailAgent] review inconclusive — flagging for human review")
        result["status"] = "needs_review"
        result["email"] = {"subject": subject, "body": body}
        result["review"] = review
        return result

    # ---- Approved from here on ----
    result["email"] = {"subject": subject, "body": body}
    result["review"] = review

    if not professor_email:
        print(f"[EmailAgent] no email address for {professor_name}, leaving as draft-only")
        result["status"] = "drafted"
        result["error"] = None
        result["review"]["reason"] = result["review"].get("reason") or "Professor email not available"
        return result

    if not authorize_send:
        print(f"[EmailAgent] drafted for {professor_name}, awaiting human approval to send")
        result["status"] = "drafted"
        return result

    # ---- Send ----
    try:
        await send_email(professor_email, subject, body)
        print(f"[EmailAgent] sent to {professor_email}")
        result["status"] = "sent"
        return result
    except Exception as e:
        print(f"[EmailAgent] send failed: {e}")
        result["status"] = "send_failed"
        result["error"] = str(e)
        return result