from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KB_ROOT = ROOT / "knowledge_base"
INDEX_PATH = KB_ROOT / "index.json"


SERVER_INFO = {"name": "python-notes-knowledge-base", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"


def load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"entries": []}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def load_entry(entry_id: str) -> dict[str, Any]:
    path = KB_ROOT / "entries" / f"{entry_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"entry not found: {entry_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def search_entries(query: str, limit: int = 10) -> list[dict[str, Any]]:
    query_lower = query.strip().lower()
    if not query_lower:
        return []
    entries = load_index().get("entries", [])
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in entries:
        entry = load_entry(item["id"])
        haystack = "\n".join(
            [
                entry.get("title", ""),
                entry.get("summary", ""),
                " ".join(entry.get("tags", [])),
                "\n".join(message.get("content", "") for message in entry.get("messages", [])),
            ]
        ).lower()
        score = haystack.count(query_lower)
        if score > 0:
            scored.append(
                (
                    score,
                    {
                        "id": entry["id"],
                        "title": entry["title"],
                        "source": entry["source"],
                        "created_at": entry["created_at"],
                        "summary": entry["summary"],
                        "tags": entry["tags"],
                    },
                )
            )
    scored.sort(key=lambda pair: (-pair[0], pair[1]["created_at"]), reverse=False)
    return [item for _, item in scored[:limit]]


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        decoded = line.decode("utf-8").strip()
        if not decoded:
            break
        name, value = decoded.split(":", 1)
        headers[name.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    payload = sys.stdin.buffer.read(length)
    return json.loads(payload.decode("utf-8"))


def write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def success_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_initialize(request_id: Any) -> dict[str, Any]:
    return success_response(
        request_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": {"tools": {}},
        },
    )


def handle_tools_list(request_id: Any) -> dict[str, Any]:
    return success_response(
        request_id,
        {
            "tools": [
                {
                    "name": "search",
                    "description": "Search local conversation knowledge base entries by keyword.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Keyword or phrase to search."},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "read",
                    "description": "Read a single knowledge base entry by id.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Knowledge base entry id."},
                        },
                        "required": ["id"],
                    },
                },
            ]
        },
    )


def make_text_content(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    try:
        if tool_name == "search":
            query = str(arguments.get("query", "")).strip()
            limit = int(arguments.get("limit", 10))
            results = search_entries(query=query, limit=limit)
            return success_response(request_id, {"content": [make_text_content(json.dumps({"results": results}, ensure_ascii=False, indent=2))]})
        if tool_name == "read":
            entry_id = str(arguments.get("id", "")).strip()
            entry = load_entry(entry_id)
            return success_response(request_id, {"content": [make_text_content(json.dumps(entry, ensure_ascii=False, indent=2))]})
        return error_response(request_id, -32601, f"unknown tool: {tool_name}")
    except FileNotFoundError as exc:
        return error_response(request_id, -32004, str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(request_id, -32000, str(exc))


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        return handle_initialize(request_id)
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return handle_tools_list(request_id)
    if method == "tools/call":
        return handle_tools_call(request_id, message.get("params", {}))
    if request_id is None:
        return None
    return error_response(request_id, -32601, f"unsupported method: {method}")


def main() -> None:
    while True:
        message = read_message()
        if message is None:
            break
        response = handle_request(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    main()
