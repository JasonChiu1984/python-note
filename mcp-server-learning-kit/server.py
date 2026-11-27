"""唯讀 MCP 示範（規格 2026-07-28，MCP Python SDK 2.x）：固定合成資料，不讀檔、不連外、不寫入。

2026-07-28 規格是無狀態的：沒有 initialize 握手，也沒有 Mcp-Session-Id。
每個請求都在 _meta 宣告版本及 client 能力；沒有能力時使用空物件。server 提供 server/discover。
"""
import argparse
import sys
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

mcp = MCPServer("Synthetic engineering notes", version="2.0.0")
NOTES = (
    {"id": "pump", "title": "Pump", "summary": "模擬泵浦壓差"},
    {"id": "temperature", "title": "Temperature", "summary": "模擬送風溫度"},
)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def search_notes(
    query: Annotated[str, Field(min_length=1, max_length=32)],
    limit: Annotated[int, Field(ge=1, le=2)] = 2,
) -> list[dict[str, str]]:
    """依固定的假資料查詢；空白查詢不接受。"""
    needle = query.strip().casefold()
    if not needle:
        raise ToolError("查詢不能只有空白")
    # 舊規格的 Logging 功能已列為 Deprecated；stdio 伺服器的診斷訊息寫到 stderr。
    print("search_notes: accepted", file=sys.stderr)
    return [
        dict(note) for note in NOTES
        if needle in (note["title"] + " " + note["summary"]).casefold()
    ][:limit]


@mcp.resource("demo://notes/about")
def dataset_info() -> str:
    """說明資料來源。"""
    return "只提供固定合成資料，不代表真實設備狀態。"


@mcp.prompt()
def summarize_notes(topic: str) -> str:
    """回傳範本文字；不會自動查詢工具。"""
    return "請依已確認資料整理主題：" + topic[:100]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    args = parser.parse_args()
    if args.transport == "streamable-http":
        # 只綁本機；對外部署要再加 TLS、身分驗證與反向代理。
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
    else:
        mcp.run(transport="stdio")
