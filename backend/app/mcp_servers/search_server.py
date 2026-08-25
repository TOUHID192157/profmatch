"""
MCP server exposing ProfMatch's search/email tools over the Model
Context Protocol. Run standalone (this file's __main__ block) — the
FastAPI backend connects to it as an MCP client over stdio and lets
Gemini decide which of these tools to call and when.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from fastmcp import FastMCP

from app.services.search_service import (
    search_professors_web,
    extract_professors_with_gemini,
    find_missing_email,
)

mcp = FastMCP("profmatch-search")


@mcp.tool()
async def search_professors(research_interests: str) -> list[dict]:
    """
    Search the web for professors whose research matches the given
    interests. Returns a list of raw professor candidates (name,
    university, department, email if found, research_areas,
    profile_url). Email may be empty — use find_professor_email to
    look it up separately if needed.
    """
    raw_results = await search_professors_web(research_interests)
    professors = await extract_professors_with_gemini(raw_results)
    return professors


@mcp.tool()
async def find_professor_email(name: str, university: str) -> str:
    """
    Search for a specific professor's email address when it wasn't
    found in the initial search. Returns the email address as a
    string, or an empty string if none could be found.
    """
    return await find_missing_email(name, university)


if __name__ == "__main__":
    mcp.run(transport="stdio")