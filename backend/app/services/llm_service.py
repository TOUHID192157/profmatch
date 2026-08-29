"""
Unified LLM provider layer.

Provider order: Groq (primary, fast + generous free tier) -> Gemini
(fallback, rotated across multiple keys) -> gorouter.app (last resort,
single-turn calls only).

Two interfaces:
  - call_llm(prompt) -> str
      Simple single-turn text generation.
  - call_llm_with_tools(system_prompt, user_message, tools, execute_tool)
      Multi-turn function-calling agent loop (used by research_agent.py).
      Groq and Gemini use different tool-schema formats internally,
      handled transparently here.
"""

import asyncio
import json
from typing import Awaitable, Callable

import httpx
from google import genai
from google.genai import types as genai_types
from groq import Groq

from app.core.config import settings
from app.core.key_rotation import get_next_gemini_key, gemini_key_count

GEMINI_MODEL = "gemini-flash-latest"
GROQ_MODEL = "openai/gpt-oss-120b"
MAX_AGENT_TURNS = 8
_BACKOFF_SCHEDULE = [2, 5, 10]


class LLMUnavailableError(Exception):
    """Raised when every configured LLM provider/key has failed."""
    pass


def _is_retryable(error_message: str) -> bool:
    return any(
        marker in error_message
        for marker in [
            "RESOURCE_EXHAUSTED", "429",
            "UNAVAILABLE", "503",
            "DEADLINE_EXCEEDED", "504", "timeout",
        ]
    )


def strip_json_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


# ---------------------------------------------------------------------
# Simple single-turn calls
# ---------------------------------------------------------------------

async def _try_groq_once(prompt: str) -> str:
    def _sync_call() -> str:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        return (response.choices[0].message.content or "").strip()

    return await asyncio.to_thread(_sync_call)


async def _try_gemini_once(prompt: str) -> str:
    def _sync_call() -> str:
        client = genai.Client(api_key=get_next_gemini_key())
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
        return (response.text or "").strip()

    return await asyncio.to_thread(_sync_call)


async def _try_gorouter(prompt: str) -> str:
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
    Simple single-turn LLM call: Groq first, then Gemini (all rotated
    keys), then gorouter.app, then raises LLMUnavailableError.
    """
    errors: list[str] = []

    if settings.groq_api_key:
        print("[LLM] Trying Groq (primary)")
        try:
            result = await _try_groq_once(prompt)
            print("[LLM] Groq succeeded")
            return result
        except Exception as e:
            print(f"[LLM] Groq failed: {str(e)[:150]}")
            errors.append(f"groq: {str(e)[:150]}")

    gemini_attempts = max(gemini_key_count(), 1)
    print(f"[LLM] Falling back to Gemini, gemini_key_count() = {gemini_key_count()}")

    for attempt in range(gemini_attempts):
        print(f"[LLM] Gemini key-attempt {attempt + 1}/{gemini_attempts}: START")
        try:
            result = await _try_gemini_once(prompt)
            print(f"[LLM] Gemini key-attempt {attempt + 1}: SUCCESS")
            return result
        except Exception as e:
            msg = str(e)
            retryable = _is_retryable(msg)
            print(f"[LLM] Gemini key-attempt {attempt + 1}: FAILED "
                  f"({'retryable' if retryable else 'non-retryable'})")
            errors.append(f"gemini[{attempt}]: {msg[:150]}")
            if not retryable:
                break
        if attempt < len(_BACKOFF_SCHEDULE):
            await asyncio.sleep(_BACKOFF_SCHEDULE[attempt])

    print("[LLM] Falling back to gorouter")
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


# ---------------------------------------------------------------------
# Multi-turn, function-calling (agent/tool-use) calls
# ---------------------------------------------------------------------

def _clean_groq_schema(schema):
    """
    Groq's tool schema validator requires lowercase JSON Schema type
    values ("string", "object") and rejects extra metadata fields.
    Gemini's SDK round-trips types to UPPERCASE enums (e.g. "STRING")
    when you call .model_dump() on its Schema object — this fixes
    both issues recursively.
    """
    if isinstance(schema, dict):
        cleaned = {
            k: _clean_groq_schema(v)
            for k, v in schema.items()
            if k not in {"title", "$defs", "$schema", "additionalProperties"}
        }
        if "type" in cleaned and isinstance(cleaned["type"], str):
            cleaned["type"] = cleaned["type"].lower()
        return cleaned
    if isinstance(schema, list):
        return [_clean_groq_schema(item) for item in schema]
    return schema


def _gemini_tool_to_groq_tool(tool: genai_types.FunctionDeclaration) -> dict:
    """Convert a Gemini-style FunctionDeclaration into Groq's
    OpenAI-compatible tool schema."""
    raw_params = tool.parameters or {"type": "object", "properties": {}}
    if hasattr(raw_params, "model_dump"):
        raw_params = raw_params.model_dump(exclude_none=True)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": _clean_groq_schema(raw_params),
        },
    }


async def _call_llm_with_tools_groq(
    system_prompt: str,
    user_message: str,
    tool_declarations: list,
    execute_tool: Callable[[str, dict], Awaitable[str]],
    max_turns: int,
) -> dict:
    """Groq's OpenAI-compatible function-calling loop."""
    groq_tools = [_gemini_tool_to_groq_tool(t) for t in tool_declarations]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    def _sync_call(use_tools: bool):
        client = Groq(api_key=settings.groq_api_key)
        kwargs = dict(model=GROQ_MODEL, messages=messages, max_tokens=4096)
        if use_tools:
            kwargs["tools"] = groq_tools
            kwargs["tool_choice"] = "auto"
        return client.chat.completions.create(**kwargs)

    for turn in range(max_turns):
        print(f"[Diag][Groq] Turn {turn + 1} START")

        try:
            response = await asyncio.to_thread(_sync_call, True)
        except Exception as e:
            if "'json'" in str(e) and "not in req" in str(e):
                print(f"[Diag][Groq] Turn {turn + 1}: model hallucinated a 'json' tool — retrying without tools")
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Give your final answer now as a plain JSON "
                            "object in your message text. Do not call any tool."
                        ),
                    }
                )
                response = await asyncio.to_thread(_sync_call, False)
            else:
                raise

        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        print(f"[Diag][Groq] Turn {turn + 1}: tool_calls={len(tool_calls)}")

        if not tool_calls:
            text = strip_json_fences(message.content or "")
            print(f"[Diag][Groq] Turn {turn + 1}: FINAL RESPONSE (raw, first 2000 chars):")
            print(text[:2000])
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                print(f"[Diag][Groq] JSON parse FAILED: {e}")
                return {"status": "error", "error": "Could not parse final JSON.", "raw_text": text}

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )

        # THIS is the piece that was missing: actually run each tool
        # and feed its result back into the conversation.
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}
            print(f"[Diag][Groq] Turn {turn + 1}: executing tool '{tc.function.name}'")
            result_text = await execute_tool(tc.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                }
            )

    # Finalization phase: tools are used up — force a plain-text JSON
    # answer from whatever tool results are already in the conversation,
    # rather than letting the model try (and fail) to call more tools.
    print("[Diag][Groq] max_turns reached — forcing finalization without tools")
    messages.append(
        {
            "role": "user",
            "content": (
                "You have used all your available tool calls. Using "
                "ONLY the tool results already in this conversation, "
                "produce your final JSON answer now. Do not call any tool."
            ),
        }
    )
    try:
        response = await asyncio.to_thread(_sync_call, False)
        text = strip_json_fences(response.choices[0].message.content or "")
        return json.loads(text)
    except Exception as e:
        print(f"[Diag][Groq] finalization failed: {e}")
        return {"status": "error", "error": f"Groq agent did not finish within {max_turns} turns."}


async def _call_llm_with_tools_gemini(
    system_prompt: str,
    user_message: str,
    tool_declarations: list,
    execute_tool: Callable[[str, dict], Awaitable[str]],
    max_turns: int,
) -> dict:
    """Gemini's function-calling loop (original implementation)."""
    contents = [
        genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)])
    ]
    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[genai_types.Tool(function_declarations=tool_declarations)],
    )

    gemini_attempts = max(gemini_key_count(), 1)

    for turn in range(max_turns):
        print(f"[Diag][Gemini] Turn {turn + 1} START")
        response = None
        turn_errors: list[str] = []

        for attempt in range(gemini_attempts):
            def _sync_call():
                client = genai.Client(api_key=get_next_gemini_key())
                return client.models.generate_content(
                    model=GEMINI_MODEL, contents=contents, config=config
                )

            try:
                response = await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=35)
                print(f"[Diag][Gemini] Turn {turn + 1}, key-attempt {attempt + 1}: SUCCESS")
                break
            except asyncio.TimeoutError:
                print(f"[Diag][Gemini] Turn {turn + 1}, key-attempt {attempt + 1}: HARD TIMEOUT")
                turn_errors.append(f"gemini[{attempt}]: hard timeout")
            except Exception as e:
                msg = str(e)
                retryable = _is_retryable(msg)
                print(f"[Diag][Gemini] Turn {turn + 1}, key-attempt {attempt + 1}: FAILED "
                      f"({'retryable' if retryable else 'non-retryable'})")
                turn_errors.append(f"gemini[{attempt}]: {msg[:150]}")
                if not retryable:
                    break
            if attempt < len(_BACKOFF_SCHEDULE):
                await asyncio.sleep(_BACKOFF_SCHEDULE[attempt])

        if response is None:
            raise LLMUnavailableError(
                "All Gemini keys failed during agent turn. Details: " + " | ".join(turn_errors)
            )

        candidate = response.candidates[0]
        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        if not function_calls:
            text = strip_json_fences(response.text or "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"status": "error", "error": "Could not parse final JSON.", "raw_text": text}

        contents.append(candidate.content)

        for fc in function_calls:
            result_text = await execute_tool(fc.name, dict(fc.args))
            contents.append(
                genai_types.Content(
                    role="user",
                    parts=[
                        genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=fc.name, response={"result": result_text}
                            )
                        )
                    ],
                )
            )

    return {"status": "error", "error": f"Agent did not finish within {max_turns} turns."}


async def call_llm_with_tools(
    system_prompt: str,
    user_message: str,
    tool_declarations: list,
    execute_tool: Callable[[str, dict], Awaitable[str]],
    max_turns: int = MAX_AGENT_TURNS,
) -> dict:
    """
    Multi-turn function-calling agent loop: tries Groq first (fast,
    generous free tier), falls back to Gemini (rotated keys) if Groq
    is unavailable or fails.
    """
    if settings.groq_api_key:
        print("[LLM] call_llm_with_tools: trying Groq (primary)")
        try:
            return await _call_llm_with_tools_groq(
                system_prompt, user_message, tool_declarations, execute_tool, max_turns
            )
        except Exception as e:
            print(f"[LLM] Groq agent loop failed, falling back to Gemini: {str(e)[:150]}")

    print("[LLM] call_llm_with_tools: using Gemini")
    return await _call_llm_with_tools_gemini(
        system_prompt, user_message, tool_declarations, execute_tool, max_turns
    )