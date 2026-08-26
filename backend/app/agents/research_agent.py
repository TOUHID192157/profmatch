"""
Research Agent — professor discovery and relevance evaluation.

Connects to the MCP search server via stdio and delegates all
Gemini/tool-calling logic to the unified LLM service.
"""

import asyncio
import os
import sys
from typing import Any

from google.genai import types as genai_types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.services.llm_service import (
    LLMUnavailableError,
    call_llm_with_tools,
)


_SERVER_SCRIPT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "mcp_servers",
        "search_server.py",
    )
)

# Prevent a stuck MCP/LLM operation from blocking the request indefinitely.
OVERALL_TIMEOUT_SECONDS = 540

# Maximum Gemini tool-calling turns for one research run.
DEFAULT_MAX_TURNS = 4

_UNSUPPORTED_SCHEMA_KEYS = {
    "title",
    "$defs",
    "$schema",
    "additionalProperties",
}


def _sanitize_schema(schema: Any) -> Any:
    """
    Recursively remove JSON Schema fields that Gemini's
    FunctionDeclaration parser does not support.
    """
    if isinstance(schema, dict):
        return {
            key: _sanitize_schema(value)
            for key, value in schema.items()
            if key not in _UNSUPPORTED_SCHEMA_KEYS
        }

    if isinstance(schema, list):
        return [_sanitize_schema(item) for item in schema]

    return schema


def _mcp_tool_to_gemini_schema(
    tool: Any,
) -> genai_types.FunctionDeclaration:
    return genai_types.FunctionDeclaration(
        name=tool.name,
        description=tool.description or "",
        parameters=_sanitize_schema(tool.inputSchema or {}),
    )


def _normalize_professors(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []

    return [
        professor
        for professor in raw
        if isinstance(professor, dict)
    ]


def _normalize_result(result: Any) -> dict:
    if not isinstance(result, dict):
        return {
            "status": "error",
            "error": "LLM returned a non-object final result.",
            "professors": [],
        }

    professors = _normalize_professors(
        result.get("professors", [])
    )

    status = result.get("status")

    if status not in {"success", "no_results", "error"}:
        status = "success" if professors else "no_results"

    normalized = {
        "status": status,
        "professors": professors,
    }

    if result.get("error"):
        normalized["error"] = str(result["error"])

    return normalized


_SYSTEM_PROMPT = """
You are the Research Agent in a multi-agent system.

Your ONLY responsibility is to find professors whose research matches
the student's research interests and evaluate their relevance.

You MUST NOT:
- Draft emails.
- Send emails.
- Invent professor information.
- Invent student information.
- Perform unrelated tasks.

AVAILABLE TOOLS:

1. search_professors(research_interests)
   Searches the web for candidate professors.

2. find_professor_email(name, university)
   Searches for a missing professor email address.

WORKFLOW:

1. Start by calling search_professors using the student's research
   interests.

2. Review the returned candidates.

3. Evaluate relevance using ONLY the student's stated interests and
   the professor's available research information.

4. Assign each professor a relevance_score between 0.0 and 1.0.

5. Provide a concise one-sentence reason explaining the match.

6. For highly relevant professors whose email is missing, use
   find_professor_email.

7. Use email lookup selectively and avoid wasting turns on weak
   candidates.

8. Prefer quality and relevance over quantity.

IMPORTANT:
- Never invent an email address.
- If an email cannot be found, use an empty string.
- Never invent a department.
- Never invent research areas.
- Never fabricate student or professor facts.

When finished, return ONLY valid JSON.

Successful response:

{
  "status": "success",
  "professors": [
    {
      "name": "...",
      "university": "...",
      "department": "...",
      "research_area": "...",
      "relevance_score": 0.0,
      "email": "...",
      "reason": "..."
    }
  ]
}

No results:

{
  "status": "no_results",
  "professors": []
}

Serious failure:

{
  "status": "error",
  "error": "...",
  "professors": []
}

Return JSON only.
No markdown.
No code fences.
No explanation outside the JSON.
"""


async def run_research_agent(
    research_interests: str,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict:

    research_interests = (research_interests or "").strip()

    if not research_interests:
        return {
            "status": "error",
            "error": "Research interests are required.",
            "professors": [],
        }

    if max_turns < 1:
        max_turns = DEFAULT_MAX_TURNS

    print("[ResearchAgent] starting search")

    async def _run() -> dict:
        if not os.path.exists(_SERVER_SCRIPT):
            raise FileNotFoundError(
                f"MCP search server not found: {_SERVER_SCRIPT}"
            )

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[_SERVER_SCRIPT],
            env=os.environ.copy(),
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                await session.initialize()

                tools_response = await session.list_tools()

                if not tools_response.tools:
                    return {
                        "status": "error",
                        "error": "MCP search server exposed no tools.",
                        "professors": [],
                    }

                gemini_tools = [
                    _mcp_tool_to_gemini_schema(tool)
                    for tool in tools_response.tools
                ]

                print(
                    "[ResearchAgent] MCP tools:",
                    ", ".join(
                        tool.name
                        for tool in tools_response.tools
                    ),
                )

                async def execute_tool(
                    tool_name: str,
                    tool_args: dict,
                ) -> str:

                    print(
                        f"[ResearchAgent] calling tool: "
                        f"{tool_name} args={tool_args}"
                    )

                    try:
                        result = await session.call_tool(
                            tool_name,
                            tool_args,
                        )

                        text_parts: list[str] = []

                        for block in result.content:
                            if hasattr(block, "text") and block.text:
                                text_parts.append(str(block.text))

                        output = "\n".join(text_parts).strip()

                        if not output:
                            return '{"result": "Tool returned no text."}'

                        return output

                    except Exception as exc:
                        error_message = str(exc)[:300]

                        print(
                            f"[ResearchAgent] tool "
                            f"'{tool_name}' failed: {error_message}"
                        )

                        safe_error = (
                            error_message
                            .replace('"', "'")
                            .replace("\n", " ")
                        )

                        return (
                            '{"error": "'
                            f"Tool {tool_name} failed: {safe_error}"
                            '"}'
                        )

                result = await call_llm_with_tools(
                    system_prompt=_SYSTEM_PROMPT,
                    user_message=(
                        "Student research interests: "
                        f'"{research_interests}"'
                    ),
                    tool_declarations=gemini_tools,
                    execute_tool=execute_tool,
                    max_turns=max_turns,
                )

                normalized = _normalize_result(result)

                print(
                    "[ResearchAgent] done, "
                    f"status={normalized['status']}, "
                    f"professors={len(normalized['professors'])}"
                )

                return normalized

    try:
        return await asyncio.wait_for(
            _run(),
            timeout=OVERALL_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        print(
            "[ResearchAgent] timed out after "
            f"{OVERALL_TIMEOUT_SECONDS}s"
        )

        return {
            "status": "error",
            "error": "Research agent timed out.",
            "professors": [],
        }

    except LLMUnavailableError as exc:
        print(
            "[ResearchAgent] all LLM providers failed:",
            exc,
        )

        return {
            "status": "error",
            "error": "All LLM providers are currently unavailable.",
            "professors": [],
        }

    except Exception as exc:
        print(
            "[ResearchAgent] failed:",
            exc,
        )

        return {
            "status": "error",
            "error": str(exc),
            "professors": [],
        }


def run_research_agent_sync(
    research_interests: str,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict:
    """
    Synchronous wrapper used by the Orchestrator.

    On Windows, MCP stdio requires the Proactor event-loop policy.
    Render/Linux uses the normal asyncio event loop.
    """

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            run_research_agent(
                research_interests,
                max_turns,
            )
        )

    finally:
        try:
            loop.run_until_complete(
                loop.shutdown_asyncgens()
            )
        except Exception:
            pass

        asyncio.set_event_loop(None)
        loop.close()