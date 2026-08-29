"""
Research Agent — professor discovery and relevance evaluation.

Connects to the MCP search server via stdio and delegates all
Gemini/tool-calling logic to the unified LLM service.

DIAGNOSTIC VERSION: includes [Diag] logging at every stage boundary
(MCP connection, tool discovery, Gemini turns, tool execution) to
isolate exactly where hangs occur.
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
    call_llm,
    strip_json_fences,
)
import json as _json


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
DEFAULT_MAX_TURNS = 8

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

1. Call search_professors EXACTLY ONCE using the student's research
   interests, in their original wording.

2. Do NOT call search_professors again — not with reworded queries,
   not with narrower terms, not to "double-check." One search result
   is what you have to work with.

3. Immediately after receiving the search results, analyze them and
   produce your final answer. Do not search again to try to get more
   or better results.

4. Evaluate relevance based ONLY on the student's stated interests
   and the professor's available research information.

5. Assign every professor a relevance_score between 0.0 and 1.0.

6. Provide a concise one-sentence reason explaining the match.

7. For highly relevant professors whose email is missing, use
   find_professor_email — this tool may be called multiple times,
   once per professor, but only for the top few most relevant
   candidates.

8. Prefer quality and relevance over producing a large number of
   professors.

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
When giving your final answer, respond with plain text containing
ONLY the JSON object — do NOT call any tool named "json" or similar.
Simply write the JSON directly as your message content.
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

        print("[Diag] MCP connection START")
        async with stdio_client(server_params) as (read, write):
            print("[Diag] MCP connection SUCCESS (stdio streams ready)")
            async with ClientSession(read, write) as session:
                print("[Diag] MCP session created")

                print("[Diag] MCP session.initialize() START")
                await session.initialize()
                print("[Diag] MCP session.initialize() SUCCESS")

                print("[Diag] MCP tools discovery START")
                tools_response = await session.list_tools()
                print("[Diag] MCP tools discovery SUCCESS")

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

                _search_professors_called = {"count": 0}
                _email_lookup_attempted: set[tuple[str, str]] = set()
                _MAX_EMAIL_LOOKUPS_PER_RUN = 3
                _captured_search_output = {"text": None}

                async def execute_tool(
                    tool_name: str,
                    tool_args: dict,
                ) -> str:
                    """
                    Execute an MCP tool safely.

                    Tool failures are returned to the LLM as structured
                    error text instead of crashing the entire agent run.
                    A programmatic guard blocks repeat calls to
                    search_professors — if the model tries anyway, it
                    gets a message telling it to use the existing
                    results instead of an actual re-search.
                    """
                    if tool_name == "search_professors":
                        if _search_professors_called["count"] >= 1:
                            print(
                                "[Diag] BLOCKED repeat search_professors call — "
                                "returning guard message instead"
                            )
                            return (
                                '{"error": "You already called search_professors. '
                                'Analyze the existing results and produce the final '
                                'answer now instead of searching again."}'
                            )
                        _search_professors_called["count"] += 1
                    if tool_name == "find_professor_email":
                        raw_name = str(tool_args.get("name", "")).strip().lower()
                        raw_university = str(tool_args.get("university", "")).strip().lower()
                        key = (raw_name, raw_university)

                        if key in _email_lookup_attempted:
                            print(
                                f"[Diag] BLOCKED repeat find_professor_email for {key} — "
                                "already attempted once"
                            )
                            return (
                                '{"error": "Email lookup for this professor was already '
                                'attempted. If it returned empty, leave the email field '
                                'empty and move on — do not retry."}'
                            )

                        if len(_email_lookup_attempted) >= _MAX_EMAIL_LOOKUPS_PER_RUN:
                            print(
                                f"[Diag] BLOCKED find_professor_email — "
                                f"reached max lookups per run ({_MAX_EMAIL_LOOKUPS_PER_RUN})"
                            )
                            return (
                                '{"error": "Maximum email lookups reached for this run. '
                                'Proceed to the final answer using what you have — leave '
                                'remaining email fields empty rather than looking up more."}'
                            )

                        _email_lookup_attempted.add(key) 

                    print(f"[Diag] MCP tool call START: {tool_name}")
                    print(
                        f"[ResearchAgent] calling tool: "
                        f"{tool_name} args={tool_args}"
                    )

                    try:
                        print(f"[Diag] MCP request SENT: {tool_name}")
                        result = await session.call_tool(
                            tool_name,
                            tool_args,
                        )
                        print(f"[Diag] MCP response RECEIVED: {tool_name}")

                        text_parts: list[str] = []

                        for block in result.content:
                            if hasattr(block, "text") and block.text:
                                text_parts.append(str(block.text))

                        output = "\n".join(text_parts).strip()

                        if tool_name == "search_professors" and output and _captured_search_output["text"] is None:
                            _captured_search_output["text"] = output

                        print(f"[Diag] MCP response PARSED: {tool_name}")
                        print(f"[Diag] {tool_name} RAW OUTPUT LENGTH: {len(output)} chars")
                        print(f"[Diag] {tool_name} RAW OUTPUT CONTENT:")
                        print(output[:3000])  # first 3000 chars, enough to see structure
                        print(f"[Diag] MCP tool call END: {tool_name}")

                        if not output:
                            print(f"[Diag] {tool_name}: OUTPUT IS EMPTY")
                            return '{"result": "Tool returned no text."}'

                        return output

                    except Exception as exc:
                        error_message = str(exc)[:300]

                        print(
                            f"[Diag] MCP tool call FAILED: {tool_name} — {error_message}"
                        )
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

                print("[Diag] call_llm_with_tools START")
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
                print("[Diag] call_llm_with_tools SUCCESS")

                normalized = _normalize_result(result)

                if (
                    normalized["status"] == "error"
                    and not normalized["professors"]
                    and _captured_search_output["text"]
                ):
                    print("[Diag] Model reported guard message as error — synthesizing final answer from captured search results")
                    synthesis_prompt = f"""You are given raw candidate professor data below, already
retrieved for a student with these research interests: "{research_interests}"

RAW CANDIDATES:
{_captured_search_output["text"][:6000]}

Evaluate relevance and produce ONLY a JSON object in this exact shape,
no markdown, no other text:
{{
  "status": "success",
  "professors": [
    {{
      "name": "...",
      "university": "...",
      "department": "...",
      "research_area": "...",
      "relevance_score": 0.0,
      "email": "...",
      "reason": "..."
    }}
  ]
}}
If no professors are clearly relevant, return {{"status": "no_results", "professors": []}}.
"""
                    try:
                        synthesis_text = strip_json_fences(await call_llm(synthesis_prompt))
                        synthesis_result = _json.loads(synthesis_text)
                        normalized = _normalize_result(synthesis_result)
                        print(f"[Diag] Synthesis fallback succeeded, status={normalized['status']}, professors={len(normalized['professors'])}")
                    except Exception as e:
                        print(f"[Diag] Synthesis fallback failed: {e}")

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