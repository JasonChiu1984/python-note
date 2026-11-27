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


def require(ok: bool, check: str) -> None:
    if not ok:
        raise RuntimeError(f"MCP smoke failed: {check}")


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
        require(client.protocol_version == PROTOCOL, "protocol version")
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        search = tools.get("search_notes")
        require(search is not None, "search_notes is listed")
        require("query" in search.input_schema.get("properties", {}), "query in tool schema")
        require(search.annotations is not None and search.annotations.read_only_hint is True,
                "read-only tool annotation")
        hit = await client.call_tool("search_notes", {"query": "Pump", "limit": 1})
        require(not hit.is_error and "pump" in repr(hit.structured_content), "valid search returns pump")
        invalid = await client.call_tool("search_notes", {"query": "Pump", "limit": 0})
        require(invalid.is_error, "out-of-range limit rejected")
        blank = await client.call_tool("search_notes", {"query": " "})
        require(blank.is_error, "blank query rejected")
        resources = (await client.list_resources()).resources
        require(any(str(resource.uri) == "demo://notes/about" for resource in resources),
                "demo resource is listed")
        info = await client.read_resource("demo://notes/about")
        require(any("合成資料" in getattr(item, "text", "") for item in info.contents),
                "resource identifies synthetic data")
        prompts = (await client.list_prompts()).prompts
        require(any(prompt.name == "summarize_notes" for prompt in prompts),
                "summarize_notes is listed")
        prompt = await client.get_prompt("summarize_notes", {"topic": "pump"})
        require(any("pump" in getattr(message.content, "text", "") for message in prompt.messages),
                "prompt expands the topic")
        print("PASS", client.protocol_version, client.server_info.name, "HTTP" if http else "STDIO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http", action="store_true")
    asyncio.run(main(parser.parse_args().http))
