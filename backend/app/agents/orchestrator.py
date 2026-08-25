"""
Orchestrator Agent — coordinates Research Agent and Email Agent.
Decides the workflow order, validates results between steps,
and builds the final response.
"""

import asyncio

from .email_agent import run_email_agent
from .research_agent import run_research_agent_sync

MAX_OUTREACH = 3


async def run_orchestrator(
    student_name: str,
    student_bio: str | None,
    student_research_interests: str | None,
    authorize_send: bool = False,
) -> dict:
    print("[Orchestrator] starting workflow")

    research_result = await asyncio.to_thread(
        run_research_agent_sync, student_research_interests or student_bio or ""
    )

    if research_result.get("status") == "error":
        print("[Orchestrator] research agent errored, stopping")
        return {
            "status": "failed",
            "stage": "research",
            "error": research_result.get("error", "Unknown research error"),
            "professors_found": 0,
            "emails": [],
        }

    professors = research_result.get("professors", [])
    if not professors:
        print("[Orchestrator] no professors found, stopping")
        return {
            "status": "no_results",
            "professors_found": 0,
            "emails": [],
        }

    professors_sorted = sorted(
        professors, key=lambda p: p.get("relevance_score", 0), reverse=True
    )
    top_professors = professors_sorted[:MAX_OUTREACH]

    print(f"[Orchestrator] handing {len(top_professors)} professor(s) to Email Agent")

    email_results = []
    for professor in top_professors:
        result = await run_email_agent(
            student_name=student_name,
            student_bio=student_bio,
            student_research_interests=student_research_interests,
            professor=professor,
            authorize_send=authorize_send,
        )
        result["professor_name"] = professor.get("name", "Unknown")
        email_results.append(result)

    print("[Orchestrator] workflow complete")

    return {
        "status": "completed",
        "professors_found": len(professors),
        "professors": professors,
        "emails": email_results,
    }