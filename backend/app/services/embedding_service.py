"""
Embedding service — wraps Voyage AI's embedding API for turning student
profiles and professor research summaries into vectors for similarity
matching (see app/db/vector_store.py for the pgvector search side).
"""

import voyageai

from app.core.config import settings

DEFAULT_EMBEDDING_MODEL = "voyage-large-2"

_client: voyageai.AsyncClient | None = None


def get_voyage_client() -> voyageai.AsyncClient:
    """Lazily create the async Voyage AI client (only when actually needed)."""
    global _client
    if _client is None:
        if not settings.voyage_api_key:
            raise RuntimeError(
                "VOYAGE_API_KEY is not set. Add it to your .env file."
            )
        _client = voyageai.AsyncClient(api_key=settings.voyage_api_key)
    return _client


async def close_voyage_client() -> None:
    """
    Reset the cached AsyncClient reference on app shutdown. Voyage AI's
    client does not expose an explicit close method, so this simply
    drops our reference so a fresh client is created if needed again.
    """
    global _client
    _client = None


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

    Args:
        texts: Raw strings to embed. Empty/whitespace-only entries are
            dropped automatically rather than raising.
        input_type: "document" for content being stored/searched (e.g.
            professor profiles), or "query" for the text doing the
            searching (e.g. a student's profile when looking for matches).
        model: Voyage embedding model name.

    Returns:
        A list of embedding vectors, one per non-empty input text, in
        the same relative order. Returns an empty list if every input
        was empty — callers should check for this rather than assume
        a 1:1 index match with the original `texts` argument.
    """
    cleaned = _clean_texts(texts)
    if not cleaned:
        return []

    client = get_voyage_client()
    result = await client.embed(cleaned, model=model, input_type=input_type)
    return result.embeddings


async def embed_text(
    text: str,
    input_type: str = "document",
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float] | None:
    """
    Embed a single piece of text. Returns None (instead of raising) if
    the text is empty or whitespace-only, so callers can decide how to
    handle a missing embedding without a try/except at every call site.
    """
    embeddings = await embed_texts([text], input_type=input_type, model=model)
    return embeddings[0] if embeddings else None


async def embed_student_profile(
    research_interests: str | None,
    bio: str | None,
    skills: list[str] | None,
) -> list[float]:
    """
    Combine a student's profile fields into one text blob and embed it
    as a search query (input_type="query") — this vector is what gets
    compared against professor document embeddings.
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
        else "A graduate student seeking a research advisor in computer science."
    )

    embedding = await embed_text(combined_text, input_type="query")
    # combined_text is never empty (falls back to the default sentence
    # above), so embedding should never be None here — but guard anyway
    # since this vector is required for search to work at all.
    if embedding is None:
        raise RuntimeError("Failed to generate student profile embedding.")
    return embedding


async def embed_professor_summaries(
    professors: list[dict],
) -> list[list[float]]:
    """
    Batch-embed multiple professor profiles in one API call
    (input_type="document"), instead of one request per professor.

    Args:
        professors: dicts with optional keys "name", "department",
            "research_areas". Professors with no usable text after
            cleaning are skipped, so the result may have fewer entries
            than the input — do not assume index alignment with
            `professors` when matching results back to records.
    """
    texts = []
    for p in professors:
        name = (p.get("name") or "").strip()
        department = (p.get("department") or "").strip()
        research_areas = (p.get("research_areas") or "").strip()
        text = f"{name}, {department}. Research areas: {research_areas}".strip(", .")
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