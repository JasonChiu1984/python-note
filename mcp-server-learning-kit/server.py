"""唯讀 MCP 示範：固定合成資料，不讀檔、不連外、不寫入。"""
import argparse
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

mcp = FastMCP("Synthetic engineering notes", host="127.0.0.1", json_response=True)
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
        raise ValueError("查詢不能只有空白")
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
    mcp.run(transport=parser.parse_args().transport)
