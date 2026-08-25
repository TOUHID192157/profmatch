"""
MCP client — connects to search_server.py (spawned as a subprocess
over stdio), fetches its tool definitions, and runs an agentic loop
where Gemini decides which tools to call and when, until it produces
a final answer.
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types as genai_types

from app.core.key_rotation import get_next_gemini_key

_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "search_server.py")


def _mcp_tool_to_gemini_schema(tool) -> genai_types.FunctionDeclaration:
    """Convert an MCP tool definition into a Gemini FunctionDeclaration."""
    return genai_types.FunctionDeclaration(
        name=tool.name,
        description=tool.description or "",
        parameters=tool.inputSchema,
    )


async def run_agentic_search(research_interests: str) -> list:
    """
    Spin up the MCP search server, expose its tools to Gemini as
    function-calling tools, and let Gemini decide how to use them
    (search_professors, and find_professor_email as needed) to
    produce a final list of professor matches.
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            gemini_tools = [
                _mcp_tool_to_gemini_schema(t) for t in tools_response.tools
            ]

            client = genai.Client(api_key=get_next_gemini_key())

            prompt = f"""You are a research assistant helping a student find
matching professors. The student's research interests are:

"{research_interests}"

Use the search_professors tool to find candidate professors. For any
professor missing an email address, decide whether it's worth calling
find_professor_email to look it up (do this for at most the top 5
most relevant candidates, to conserve API calls).

When you are done, respond with ONLY a JSON array of professor
objects (name, university, department, email, research_areas,
profile_url), no other text, no markdown fences.
"""

            contents = [
                genai_types.Content(
                    role="user", parts=[genai_types.Part(text=prompt)]
                )
            ]

            config = genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(function_declarations=gemini_tools)],
            )

            max_turns = 6
            for _ in range(max_turns):
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=contents,
                    config=config,
                )

                candidate = response.candidates[0]
                function_calls = [
                    part.function_call
                    for part in candidate.content.parts
                    if part.function_call
                ]

                if not function_calls:
                    text = (response.text or "").strip()
                    if text.startswith("```"):
                        text = text.strip("`")
                        if text.startswith("json"):
                            text = text[4:]
                        text = text.strip()
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return []

                contents.append(candidate.content)

                for fc in function_calls:
                    result = await session.call_tool(fc.name, dict(fc.args))
                    result_text = "".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )

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

            return []


def run_agentic_search_sync(research_interests: str) -> list:
    """
    Synchronous wrapper that runs run_agentic_search() in a fresh
    event loop with the Windows Proactor policy, regardless of what
    policy the calling thread's loop (e.g. uvicorn's main loop) uses.
    Needed because uvicorn forces a Selector event loop on Windows,
    which does not support subprocess creation (required by MCP's
    stdio transport).
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run_agentic_search(research_interests))
    finally:
        loop.close()