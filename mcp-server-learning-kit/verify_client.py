"""以 MCP Python SDK 2.x 的 Client 實際探索與呼叫 server.py 的 smoke test（規格 2026-07-28）。"""
import argparse
import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

PROTOCOL = "2026-07-28"


async def main(http: bool) -> None:
    if http:
        target = "http://127.0.0.1:8000/mcp"
    else:
        server = Path(__file__).with_name("server.py")
        target = StdioServerParameters(command=sys.executable, args=[str(server)])
    # mode="auto"：先呼叫 server/discover 選定版本；只有舊版 server 才退回 initialize 握手。
    async with Client(target, mode="auto") as client:
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
