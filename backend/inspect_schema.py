import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "app", "mcp_servers", "search_server.py")
)


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_response = await session.list_tools()

            for tool in tools_response.tools:
                print(f"\n===== TOOL: {tool.name} =====")
                print("Description:", tool.description)
                print("Raw inputSchema (type):", type(tool.inputSchema))
                print("Raw inputSchema (content):")
                print(json.dumps(tool.inputSchema, indent=2, default=str))


asyncio.run(main())