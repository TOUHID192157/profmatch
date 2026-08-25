"""
Search service — finds professors matching a student's research profile.

Flow:
  1. Use Tavily to search the web for professors in the student's field.
  2. Use OpenRouter (Claude 3.5 Sonnet) to extract structured professor info from raw search results.
  3. Embed each professor's research summary (Voyage AI).
  4. Store professors + embeddings in Supabase.
  5. Run a pgvector similarity search to rank professors against the
     student's own profile embedding.

Both Tavily and Gemini clients are created fresh per call using the
next key in rotation (app.core.key_rotation), spreading requests
across multiple free-tier accounts to avoid rate limits.

find_missing_email() is called on-demand (one professor at a time,
triggered by the user) rather than automatically for every professor
in a search, to avoid hitting API rate limits.
"""
import asyncio
import json
import uuid
import httpx

from tavily import TavilyClient
from google import genai

from app.core.config import settings
from app.core.key_rotation import get_next_gemini_key, get_next_tavily_key
from app.db.vector_store import supabase
from app.services.embedding_service import (
    embed_professor_summaries,
    embed_student_profile,
)


def get_tavily_client() -> TavilyClient:
    """Create a Tavily client using the next key in rotation."""
    return TavilyClient(api_key=get_next_tavily_key())


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using the next key in rotation."""
    return genai.Client(api_key=get_next_gemini_key())


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
    Use Claude (via OpenRouter, a paid API) to turn raw Tavily search
    results into a clean, structured list of professor records.
    Switched from Gemini's free tier here specifically because this
    call was the most frequent source of 503 overload errors.
    """
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
        async with httpx.AsyncClient(timeout=45) as http_client:
            response = await http_client.post(
                "https://gorouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[search_service] OpenRouter extraction failed: {e}")
        return []

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        professors = json.loads(text)
    except json.JSONDecodeError:
        return []

    return professors if isinstance(professors, list) else []


async def find_missing_email(name: str, university: str) -> str:
    """
    Run a targeted search for a single professor's email address,
    triggered on-demand by the user (not automatically for every
    professor in a search, to avoid hitting rate limits).
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

    gemini = get_gemini_client()
    prompt = f"""Find the email address for {name} at {university} in the text below.
Respond with ONLY the email address if found, or an empty string if not found.
No other text, no explanation.

TEXT:
{combined_snippets}
"""
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                gemini.models.generate_content,
                model="gemini-flash-latest",
                contents=prompt,
            ),
            timeout=15,
        )
        candidate = (response.text or "").strip()
    except Exception:
        return ""

    if "@" in candidate and " " not in candidate and len(candidate) < 100:
        return candidate
    return ""


async def store_professors(user_id: str, professors: list[dict]) -> list[dict]:
    """
    Embed and store a list of professor records in Supabase, tied to
    the student (user_id) who triggered this search. Email lookup for
    missing addresses is NOT done here — it's on-demand per professor
    via find_missing_email(), triggered from the frontend.
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