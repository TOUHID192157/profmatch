"""
Search service — finds professors matching a student's research profile.

Flow:
  1. Use Tavily to search the web for professors in the student's field.
  2. Use the unified LLM service (app.services.llm_service) to extract
     structured professor info from raw search results.
  3. Embed each professor's research summary (Voyage AI).
  4. Store professors + embeddings in Supabase.
  5. Run a pgvector similarity search to rank professors against the
     student's own profile embedding.
"""

import json
import uuid
import logging
logger = logging.getLogger("mcp_search_server")

from tavily import TavilyClient

from app.core.key_rotation import get_next_tavily_key
from app.db.vector_store import supabase
from app.services.embedding_service import (
    embed_professor_summaries,
    embed_student_profile,
)
from app.services.llm_service import call_llm, strip_json_fences, LLMUnavailableError


def get_tavily_client() -> TavilyClient:
    """Create a Tavily client using the next key in rotation."""
    return TavilyClient(api_key=get_next_tavily_key())


async def search_professors_web(research_interests: str, max_results: int = 8) -> list[dict]:
    """
    Search the web (via Tavily) for professors whose research matches
    the given interests, restricted to US university (.edu) sites.
    """
    research_interests = research_interests or "computer science"
    print(f"[Diag][Tavily] START, interests={research_interests!r}")

    client = get_tavily_client()
    query = (
        f"professors researching {research_interests} "
        f"faculty profile site:.edu"
    )
    print(f"[Diag][Tavily] query = {query!r}")

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
    )

    results = response.get("results", [])
    print(f"[Diag][Tavily] results count: {len(results)}")

    return results


async def extract_professors_with_gemini(raw_results: list[dict]) -> list[dict]:
    """
    Use the unified LLM service to turn raw Tavily search results
    (titles + content snippets) into a clean, structured list of
    professor records.
    """
    print(f"[Diag][Extract] START, raw_results count={len(raw_results)}")

    if not raw_results:
        return []

    combined_snippets = "\n\n".join(
        f"URL: {r.get('url', '')}\nTitle: {r.get('title', '')}\n"
        f"Content: {r.get('content', '')[:1000]}"
        for r in raw_results
    )

    prompt = f"""You are extracting professor faculty profiles from web search results.

From the text below, extract a JSON array of professors. For each professor include:
- "name": full name
- "university": university name
- "department": department/school if mentioned, else empty string
- "email": email address if visible, else empty string
- "research_areas": a short summary of their research focus
- "profile_url": the URL of their faculty page

Only include entries that are clearly individual faculty/professor profiles.
If no professors can be identified, return an empty array.
Respond with ONLY the JSON array, no other text, no markdown fences.

SEARCH RESULTS:
{combined_snippets}
"""

    try:
        raw_text = await call_llm(prompt)
        logger.info(f"[Extract] LLM raw response (first 500 chars): {raw_text[:500]!r}")
        text = strip_json_fences(raw_text)
    except LLMUnavailableError as e:
        logger.info(f"[Extract] LLM call failed, all providers exhausted: {e}")
        return []

    if not text:
        return []

    try:
        professors = json.loads(text)
    except json.JSONDecodeError as e:
        logger.info(f"[Extract] JSON parse FAILED: {e}")
        return []

    result = professors if isinstance(professors, list) else []
    logger.info(f"[Extract] parsed professors count={len(result)}")
    return result


async def find_missing_email(name: str, university: str) -> str:
    """
    Run a targeted search for a single professor's email address,
    triggered on-demand by the user.
    """
    client = get_tavily_client()
    query = f'"{name}" {university} email contact faculty'

    try:
        response = client.search(query=query, search_depth="basic", max_results=3)
    except Exception:
        return ""

    combined_snippets = "\n\n".join(
        f"{r.get('title', '')}\n{r.get('content', '')[:500]}"
        for r in response.get("results", [])
    )

    if not combined_snippets.strip():
        return ""

    prompt = f"""Find the email address for {name} at {university} in the text below.
Respond with ONLY the email address if found, or an empty string if not found.
No other text, no explanation.

TEXT:
{combined_snippets}
"""
    try:
        candidate = (await call_llm(prompt)).strip()
    except LLMUnavailableError:
        return ""

    if "@" in candidate and " " not in candidate and len(candidate) < 100:
        return candidate
    return ""


async def store_professors(user_id: str, professors: list[dict]) -> list[dict]:
    """
    Embed and store a list of professor records in Supabase, tied to
    the student (user_id) who triggered this search.
    """
    if not professors:
        return []

    embeddings = await embed_professor_summaries(professors)

    rows = []
    for professor, embedding in zip(professors, embeddings):
        rows.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": professor.get("name", "") or "Unknown",
            "university": professor.get("university", ""),
            "department": professor.get("department", ""),
            "email": professor.get("email", ""),
            "research_areas": professor.get("research_areas", ""),
            "profile_url": professor.get("profile_url", ""),
            "embedding": embedding,
        })

    response = supabase.table("professor_results").insert(rows).execute()
    return response.data or []


async def find_matching_professors(
    user_id: str,
    research_interests: str | None,
    bio: str | None,
    skills: list[str] | None,
    match_count: int = 10,
) -> list[dict]:
    """
    Full pipeline: search the web for professors, extract structured
    data, embed and store them, then rank them by similarity to the
    student's own profile embedding.
    """
    student_embedding = await embed_student_profile(research_interests, bio, skills)

    raw_results = await search_professors_web(research_interests or "computer science")
    professors = await extract_professors_with_gemini(raw_results)
    await store_professors(user_id, professors)

    response = supabase.rpc(
        "match_professors_by_embedding",
        {
            "query_embedding": student_embedding,
            "match_threshold": 0.3,
            "match_count": match_count,
        },
    ).execute()

    return response.data or []