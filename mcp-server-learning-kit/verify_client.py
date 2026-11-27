"""以 MCP Python SDK 2.x 的 Client 實際探索與呼叫 server.py 的 smoke test（規格 2026-07-28）。"""
import argparse
import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path

import httpx2

from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

PROTOCOL = "2026-07-28"


async def main(http: bool) -> None:
    async with AsyncExitStack() as stack:
        if http:
            # This local-only exercise must not route through the ambient proxy.
            http_client = await stack.enter_async_context(
                httpx2.AsyncClient(trust_env=False, timeout=10.0)
            )
            target = streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http_client)
        else:
            server = Path(__file__).with_name("server.py")
            target = StdioServerParameters(command=sys.executable, args=[str(server)])
        client = await stack.enter_async_context(Client(target, mode="auto"))
        assert client.protocol_version == PROTOCOL, client.protocol_version
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert "query" in tools["search_notes"].input_schema["properties"]
        assert tools["search_notes"].annotations.read_only_hint is True
        hit = await client.call_tool("search_notes", {"query": "Pump", "limit": 1})
        assert not hit.is_error and "pump" in repr(hit.structured_content)
        invalid = await client.call_tool("search_notes", {"query": "Pump", "limit": 0})
        assert invalid.is_error
        blank = await client.call_tool("search_notes", {"query": " "})
        assert blank.is_error
        resources = (await client.list_resources()).resources
        info = await client.read_resource(resources[0].uri)
        assert "合成資料" in info.contents[0].text
        assert "summarize_notes" in {p.name for p in (await client.list_prompts()).prompts}
        prompt = await client.get_prompt("summarize_notes", {"topic": "pump"})
        assert "pump" in prompt.messages[0].content.text
        print("PASS", client.protocol_version, client.server_info.name, "HTTP" if http else "STDIO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http", action="store_true")
    asyncio.run(main(parser.parse_args().http))
