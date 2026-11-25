"""經實際 MCP client 初始化、探索及呼叫的 smoke test。"""
import argparse
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def streams(http: bool):
    if http:
        async with httpx.AsyncClient(trust_env=False) as client:
            async with streamable_http_client("http://127.0.0.1:8000/mcp", http_client=client) as (r, w, _):
                yield r, w
    else:
        server = Path(__file__).with_name("server.py")
        async with stdio_client(StdioServerParameters(command=sys.executable, args=[str(server)])) as pair:
            yield pair


async def main(http: bool):
    async with streams(http) as (read, write):
        async with ClientSession(read, write) as session:
            started = await session.initialize()
            assert await session.list_tools()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert "query" in tools["search_notes"].inputSchema["properties"]
            hit = await session.call_tool("search_notes", {"query": "Pump", "limit": 1})
            assert not hit.isError and "pump" in repr(hit.structuredContent)
            invalid = await session.call_tool("search_notes", {"query": "Pump", "limit": 0})
            assert invalid.isError
            blank = await session.call_tool("search_notes", {"query": " "})
            assert blank.isError
            resources = (await session.list_resources()).resources
            info = await session.read_resource(resources[0].uri)
            assert "合成資料" in info.contents[0].text
            assert "summarize_notes" in {p.name for p in (await session.list_prompts()).prompts}
            prompt = await session.get_prompt("summarize_notes", {"topic": "pump"})
            assert "pump" in prompt.messages[0].content.text
            print("PASS", started.protocolVersion, "HTTP" if http else "STDIO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http", action="store_true")
    asyncio.run(main(parser.parse_args().http))
