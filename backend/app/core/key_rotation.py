"""
Round-robin API key rotation. Lets us configure multiple free-tier
keys (one per teammate) per service, so requests spread across them
instead of hitting one key's rate limit.
"""

import itertools

from app.core.config import settings

# ---------- Gemini ----------

_gemini_keys = [
    k
    for k in [
        settings.gemini_api_key,
        settings.gemini_api_key_2,
        settings.gemini_api_key_3,
        settings.gemini_api_key_4,
    ]
    if k
]
_gemini_cycle = itertools.cycle(_gemini_keys) if _gemini_keys else None


def get_next_gemini_key() -> str:
    """Return the next Gemini API key in rotation."""
    if _gemini_cycle is None:
        raise RuntimeError(
            "No Gemini API keys configured. Add GEMINI_API_KEY to your .env file."
        )
    return next(_gemini_cycle)


def gemini_key_count() -> int:
    return len(_gemini_keys)


# ---------- Tavily ----------

_tavily_keys = [
    k for k in [settings.tavily_api_key, settings.tavily_api_key_2] if k
]
_tavily_cycle = itertools.cycle(_tavily_keys) if _tavily_keys else None


def get_next_tavily_key() -> str:
    """Return the next Tavily API key in rotation."""
    if _tavily_cycle is None:
        raise RuntimeError(
            "No Tavily API keys configured. Add TAVILY_API_KEY to your .env file."
        )
    return next(_tavily_cycle)


def tavily_key_count() -> int:
    return len(_tavily_keys)


# ---------- Voyage AI ----------

_voyage_keys = [
    k
    for k in [
        settings.voyage_api_key,
        settings.voyage_api_key_2,
        settings.voyage_api_key_3,
    ]
    if k
]
_voyage_cycle = itertools.cycle(_voyage_keys) if _voyage_keys else None


def get_next_voyage_key() -> str:
    """Return the next Voyage AI API key in rotation."""
    if _voyage_cycle is None:
        raise RuntimeError(
            "No Voyage API keys configured. Add VOYAGE_API_KEY to your .env file."
        )
    return next(_voyage_cycle)


def voyage_key_count() -> int:
    return len(_voyage_keys)