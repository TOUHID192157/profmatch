"""
Research Agent — owns professor discovery only. Connects to the
existing MCP search server (app/mcp_servers/search_server.py) and
uses its own Gemini call, with a system prompt scoped strictly to
research, to decide when to call search_professors / find_professor_email.
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

_SERVER_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "mcp_servers", "search_server.py"
)

_SYSTEM_PROMPT = """You are the Research Agent in a multi-agent system.

Your ONLY job is to find professors matching a student's research
interests and evaluate how relevant each one is. You do not draft or
send emails — that is another agent's job.

You have two tools:
- search_professors(research_interests): searches the web for candidate professors.
- find_professor_email(name, university): looks up a missing email address.

For each professor you find, estimate a relevance_score between 0.0
and 1.0 based on how closely their research_areas match the student's
stated interests, and write a one-sentence reason explaining the match.

Call find_professor_email only for the professors you judge most
relevant (at most the top 5), if their email is missing.

When finished, respond with ONLY a JSON object, no other text, no
markdown fences, in exactly this shape:
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
If you find no suitable professors, respond with:
{"status": "no_results", "professors": []}
"""


def _mcp_tool_to_gemini_schema(tool) -> genai_types.FunctionDeclaration:
    return genai_types.FunctionDeclaration(
        name=tool.name,
        description=tool.description or "",
        parameters=tool.inputSchema,
    )


async def run_research_agent(research_interests: str) -> dict:
    print("[ResearchAgent] starting search")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
        env=os.enviorn.copy(),
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_response = await session.list_tools()
                gemini_tools = [
                    _mcp_tool_to_gemini_schema(t) for t in tools_response.tools
                ]

                client = genai.Client(api_key=get_next_gemini_key())

                contents = [
                    genai_types.Content(
                        role="user",
                        parts=[
                            genai_types.Part(
                                text=f'Student research interests: "{research_interests}"'
                            )
                        ],
                    )
                ]

                config = genai_types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    tools=[genai_types.Tool(function_declarations=gemini_tools)],
                )

                max_turns = 6
                for turn in range(max_turns):
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
                            result = json.loads(text)
                        except json.JSONDecodeError:
                            print("[ResearchAgent] failed to parse final JSON")
                            return {"status": "error", "error": "Could not parse research results.", "professors": []}

                        if "status" not in result:
                            result["status"] = "success" if result.get("professors") else "no_results"
                        print(f"[ResearchAgent] done, status={result['status']}, "
                              f"professors={len(result.get('professors', []))}")
                        return result

                    contents.append(candidate.content)

                    for fc in function_calls:
                        print(f"[ResearchAgent] calling tool: {fc.name}")
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

                print("[ResearchAgent] hit max turns without a final answer")
                return {"status": "error", "error": "Research agent did not finish in time.", "professors": []}

    except Exception as e:
        print(f"[ResearchAgent] failed: {e}")
        return {"status": "error", "error": str(e), "professors": []}


def run_research_agent_sync(research_interests: str) -> dict:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run_research_agent(research_interests))
    finally:
        loop.close()