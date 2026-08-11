"""
Search service — finds professors matching a student's research profile.

Flow:
  1. Use Tavily to search the web for professors in the student's field.
  2. Use Gemini to extract structured professor info from raw search results.
  3. Embed each professor's research summary (Voyage AI).
  4. Store professors + embeddings in Supabase.
  5. Run a pgvector similarity search to rank professors against the
     student's own profile embedding.
"""

import json
import uuid

from tavily import TavilyClient
from google import genai

from app.core.config import settings
from app.db.vector_store import supabase
from app.services.embedding_service import (
    embed_professor_summaries,
    embed_student_profile,
)

_tavily_client: TavilyClient | None = None
_gemini_client: genai.Client | None = None


def get_tavily_client() -> TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        if not settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")
        _tavily_client = TavilyClient(api_key=settings.tavily_api_key)
    return _tavily_client


def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


async def search_professors_web(research_interests: str, max_results: int = 8) -> list[dict]:
    """
    Search the web (via Tavily) for professors whose research matches
    the given interests, restricted to US university (.edu) sites.
    """
    client = get_tavily_client()
    query = (
        f"professors researching {research_interests} "
        f"faculty profile site:.edu"
    )
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
    )
    return response.get("results", [])


async def extract_professors_with_gemini(raw_results: list[dict]) -> list[dict]:
    """
    Use Gemini to turn raw Tavily search results (titles + content
    snippets) into a clean, structured list of professor records.
    """
    if not raw_results:
        return []

    client = get_gemini_client()

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

    response = client.models.generate_content(
        model="gemini-flash-latest", contents=prompt
    )

    text = (response.text or "").strip()
    # Gemini sometimes wraps JSON in markdown fences despite instructions
    if text.startswith("`"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        professors = json.loads(text)
    except json.JSONDecodeError:
        return []

    return professors if isinstance(professors, list) else []


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