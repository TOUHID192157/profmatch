"""
Embedding service — wraps Voyage AI's embedding API for turning student
profiles and professor research summaries into vectors for similarity
matching (see app/db/vector_store.py for the pgvector search side).

Each call creates a fresh AsyncClient using the next key in rotation
(app.core.key_rotation), spreading requests across multiple free-tier
Voyage accounts to avoid rate limits.
"""

import voyageai
from typing import Any

from app.core.key_rotation import get_next_voyage_key

DEFAULT_EMBEDDING_MODEL = "voyage-large-2"


def get_voyage_client() -> voyageai.AsyncClient:
    """Create a Voyage AsyncClient using the next key in rotation."""
    return voyageai.AsyncClient(api_key=get_next_voyage_key())


async def close_voyage_client() -> None:
    """
    No-op kept for compatibility with main.py's shutdown hook. Clients
    are now created fresh per call (see get_voyage_client), so there is
    no persistent client to close.
    """
    return None


def _clean_texts(texts: list[str]) -> list[str]:
    """Strip whitespace and drop empty/None entries from a list of texts."""
    return [t.strip() for t in texts if t and t.strip()]


async def embed_texts(
    texts: list[str],
    input_type: str = "document",
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[list[float]]:
    """
    Embed one or more pieces of text in a single API call (batching).
    Returns an empty list if no valid texts are provided.
    """
    cleaned = _clean_texts(texts)
    if not cleaned:
        return []

    client = get_voyage_client()
    result = await client.embed(
        cleaned, model=model, input_type=input_type, truncation=True
    )
    return result.embeddings


async def embed_text(
    text: str,
    input_type: str = "document",
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float] | None:
    """Embed a single piece of text. Returns None if empty."""
    embeddings = await embed_texts([text], input_type=input_type, model=model)
    return embeddings[0] if embeddings else None


async def embed_student_profile(
    research_interests: str | None = None,
    bio: str | None = None,
    skills: list[str] | None = None,
) -> list[float]:
    """
    Combine student profile fields into a search query vector (input_type="query").
    """
    parts: list[str] = []

    if research_interests and research_interests.strip():
        parts.append(f"Research interests: {research_interests.strip()}")
    if bio and bio.strip():
        parts.append(f"Bio: {bio.strip()}")
    if skills:
        clean_skills = _clean_texts(skills)
        if clean_skills:
            parts.append(f"Skills: {', '.join(clean_skills)}")

    combined_text = (
        "\n".join(parts)
        if parts
        else "A student seeking academic research opportunities and faculty mentorship."
    )

    embedding = await embed_text(combined_text, input_type="query")
    if embedding is None:
        raise RuntimeError("Failed to generate student profile embedding.")
    return embedding


async def embed_professor_summaries(
    professors: list[dict[str, Any]],
) -> list[list[float]]:
    """
    Batch-embed multiple professor profiles in one API call (input_type="document").
    Guarantees placeholder fallback text for empty profiles so the returned list
    maintains a 1:1 index alignment with the input list.
    """
    texts: list[str] = []
    for p in professors:
        name = (p.get("name") or "").strip()
        department = (p.get("department") or "").strip()
        research_areas = (p.get("research_areas") or "").strip()

        raw_text = f"{name}, {department}. Research areas: {research_areas}".strip(", .")
        text = raw_text if raw_text else "Faculty member with unspecified research areas."
        texts.append(text)

    return await embed_texts(texts, input_type="document")


async def embed_professor_summary(
    name: str, research_areas: str, department: str = ""
) -> list[float] | None:
    """Convenience wrapper for embedding a single professor's profile."""
    embeddings = await embed_professor_summaries(
        [{"name": name, "department": department, "research_areas": research_areas}]
    )
    return embeddings[0] if embeddings else None