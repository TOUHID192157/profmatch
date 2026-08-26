"""
Unified LLM provider layer.

Two interfaces:
  - call_llm(prompt) -> str
      For simple, single-turn text generation (extraction, drafting,
      review). Used by search_service.py, email_service.py, and
      email_agent.py's review step.
  - call_llm_with_tools(system_prompt, user_message, tools, execute_tool)
      For multi-turn, function-calling agent loops (MCP tool use).
      Used by research_agent.py. Handles the Gemini function-calling
      conversation loop internally, including key rotation.

Both share the same fallback chain: try each configured Gemini key in
rotation; if all are rate-limited/unavailable, fall back to
gorouter.app (single-turn calls only); if that also fails, raise
LLMUnavailableError so the caller can decide how to handle a total
outage.

All Gemini SDK calls (which are synchronous) are wrapped in
asyncio.to_thread() so they never block the event loop.

DIAGNOSTIC VERSION: includes [Diag] logging at every Gemini
request/response boundary to isolate exactly where hangs occur.
"""

import asyncio
import json
from typing import Awaitable, Callable

import httpx
from google import genai
from google.genai import types as genai_types

from app.core.config import settings
from app.core.key_rotation import get_next_gemini_key, gemini_key_count

GEMINI_MODEL = "gemini-flash-latest"
MAX_AGENT_TURNS = 4


class LLMUnavailableError(Exception):
    """Raised when every configured LLM provider/key has failed."""
    pass


def _is_retryable(error_message: str) -> bool:
    return any(
        marker in error_message
        for marker in [
            "RESOURCE_EXHAUSTED", "429",
            "UNAVAILABLE", "503",
            "DEADLINE_EXCEEDED", "504,"timeout",
        ]
    )


# ---------------------------------------------------------------------
# Simple single-turn calls
# ---------------------------------------------------------------------

async def _try_gemini_once(prompt: str) -> str:
    """One Gemini attempt with the next key in rotation, off the event loop."""
    def _sync_call() -> str:
        client = genai.Client(api_key=get_next_gemini_key())
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
        return (response.text or "").strip()

    return await asyncio.to_thread(_sync_call)


async def _try_gorouter(prompt: str) -> str:
    """Last-resort fallback via gorouter.app."""
    if not settings.openrouter_api_key:
        raise LLMUnavailableError("No gorouter.app API key configured.")

    async with httpx.AsyncClient(timeout=45) as http_client:
        response = await http_client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


async def call_llm(prompt: str) -> str:
    """
    Simple single-turn LLM call with full fallback: tries every
    configured Gemini key, then gorouter.app, then raises
    LLMUnavailableError if everything fails.
    """
    errors: list[str] = []

    gemini_attempts = max(gemini_key_count(), 1)
    print(f"[LLM] gemini_key_count() = {gemini_key_count()}")

    for attempt in range(gemini_attempts):
        try:
            result = await _try_gemini_once(prompt)
            print(f"[LLM] Gemini attempt {attempt + 1} succeeded")
            return result
        except Exception as e:
            msg = str(e)
            reason = "429/503 rate-limited" if _is_retryable(msg) else "non-retryable error"
            print(f"[LLM] Gemini attempt {attempt + 1} failed: {reason}")
            errors.append(f"gemini[{attempt}]: {msg[:150]}")
            if _is_retryable(msg):
                continue
            break

    print("[LLM] All Gemini keys failed, falling back to gorouter")
    try:
        result = await _try_gorouter(prompt)
        print("[LLM] gorouter succeeded")
        return result
    except Exception as e:
        print(f"[LLM] gorouter failed: {str(e)[:100]}")
        errors.append(f"gorouter: {str(e)[:150]}")

    print("[LLM] All providers exhausted")
    raise LLMUnavailableError(
        "All LLM providers failed. Details: " + " | ".join(errors)
    )


def strip_json_fences(text: str) -> str:
    """Shared helper: strip ```json ... ``` fences some models add despite instructions."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


# ---------------------------------------------------------------------
# Multi-turn, function-calling (agent/tool-use) calls
# ---------------------------------------------------------------------

async def call_llm_with_tools(
    system_prompt: str,
    user_message: str,
    tool_declarations: list,
    execute_tool: Callable[[str, dict], Awaitable[str]],
    max_turns: int = MAX_AGENT_TURNS,
) -> dict:
    """
    Run a Gemini function-calling agent loop with key rotation. The
    caller supplies:
      - tool_declarations: Gemini FunctionDeclaration objects (built
        from MCP tool schemas by the caller, e.g. research_agent.py)
      - execute_tool: an async callback(tool_name, tool_args) -> str
        that actually runs the tool (e.g. via an MCP ClientSession)

    Returns the final parsed JSON dict from the model once it stops
    requesting tool calls. Raises LLMUnavailableError only if every
    Gemini key fails on the same turn (no gorouter fallback here,
    since gorouter doesn't support this tool-calling flow).
    """
    contents = [
        genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)])
    ]
    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[genai_types.Tool(function_declarations=tool_declarations)],
    )

    gemini_attempts = max(gemini_key_count(), 1)
    print(f"[Diag] call_llm_with_tools: gemini_key_count() = {gemini_key_count()}, max_turns = {max_turns}")

    for turn in range(max_turns):
        print(f"[Diag] Gemini Turn {turn + 1} START")
        response = None
        turn_errors: list[str] = []

        for attempt in range(gemini_attempts):
            try:
                print(f"[Diag] Gemini Turn {turn + 1}, attempt {attempt + 1}: request SENT")

                def _sync_call():
                    client = genai.Client(
                        api_key=get_next_gemini_key(),
                        http_options=genai_types.HttpOptions(timeout=30_000),  # 30s, milliseconds
                    )
                    return client.models.generate_content(
                        model=GEMINI_MODEL, contents=contents, config=config
                    )
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(_sync_call), timeout=35
                    )
                except asyncio.TimeoutError:
                    print(f"[Diag] Gemini Turn {turn + 1}, attempt {attempt + 1}: HARD TIMEOUT (30s)")
                    turn_errors.append(f"gemini[{attempt}]: hard timeout after 30s")
                    continue
                print(f"[Diag] Gemini Turn {turn + 1}, attempt {attempt + 1}: response RECEIVED")
                print(f"[LLM] Turn {turn + 1}, Gemini attempt {attempt + 1} succeeded")
                break
            except Exception as e:
                import traceback
                print(f"[Diag] ===== FULL TRACEBACK: Turn {turn + 1}, attempt {attempt + 1} =====")
                traceback.print_exc()
                print(f"[Diag] ===== END TRACEBACK =====")
                msg = str(e)
                reason = "429/503 rate-limited" if _is_retryable(msg) else "non-retryable error"
                print(f"[Diag] Gemini Turn {turn + 1}, attempt {attempt + 1}: FAILED ({reason})")
                print(f"[LLM] Turn {turn + 1}, Gemini attempt {attempt + 1} failed: {reason}")
                turn_errors.append(f"gemini[{attempt}]: {msg[:150]}")
                if _is_retryable(msg):
                    continue
                break

        if response is None:
            print(f"[Diag] Gemini Turn {turn + 1}: ALL ATTEMPTS FAILED")
            raise LLMUnavailableError(
                "All Gemini keys failed during agent turn. Details: "
                + " | ".join(turn_errors)
            )

        candidate = response.candidates[0]
        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if part.function_call
        ]

        print(f"[Diag] Gemini Turn {turn + 1}: response PARSED, function_calls={len(function_calls)}")

        if not function_calls:
            text = strip_json_fences(response.text or "")
            print(f"[Diag] Gemini Turn {turn + 1}: no function calls, treating as final answer")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"status": "error", "error": "Could not parse final JSON.", "raw_text": text}

        contents.append(candidate.content)

        for fc in function_calls:
            print(f"[Diag] Gemini Turn {turn + 1}: executing tool call '{fc.name}'")
            result_text = await execute_tool(fc.name, dict(fc.args))
            print(f"[Diag] Gemini Turn {turn + 1}: tool call '{fc.name}' returned")
            contents.append(
                genai_types.Content(
                    role="user",
                    parts=[
                        genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=fc.name,
                                response={"result": result_text},
                            )
                        )
                    ],
                )
            )

        print(f"[Diag] Gemini Turn {turn + 1} END")

    print(f"[Diag] call_llm_with_tools: hit max_turns ({max_turns}) without final answer")
    return {
        "status": "error",
        "error": f"Agent did not finish within {max_turns} turns.",
    }