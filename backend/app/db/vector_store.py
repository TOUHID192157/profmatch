from supabase import create_client, Client

from app.core.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


def upsert_student_vector(user_id: str, embedding: list[float]) -> None:
    """Insert or update a student's profile embedding."""
    supabase.table("student_vectors").upsert(
        {"user_id": user_id, "embedding": embedding}
    ).execute()


def match_professors(
    query_embedding: list[float],
    match_count: int = 10,
    match_threshold: float = 0.7,
) -> list[dict]:
    """
    Find professors whose research embeddings are closest to the given
    query embedding, using cosine similarity via a Postgres RPC function.
    """
    response = supabase.rpc(
        "match_professors",
        {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count,
        },
    ).execute()
    return response.data or []


def insert_professor_result(user_id: str, professor_data: dict) -> dict:
    """Save a matched professor result for a student."""
    response = (
        supabase.table("professor_results")
        .insert({"user_id": user_id, **professor_data})
        .execute()
    )
    return response.data[0] if response.data else {}