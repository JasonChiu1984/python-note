from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def extract_message(buffer: bytes) -> tuple[dict, bytes]:
    header_end = buffer.find(b"\r\n\r\n")
    if header_end == -1:
        raise RuntimeError("MCP response missing header delimiter")
    headers = buffer[:header_end].decode("utf-8")
    content_length = None
    for line in headers.split("\r\n"):
        if line.lower().startswith("content-length:"):
            content_length = int(line.split(":", 1)[1].strip())
            break
    if content_length is None:
        raise RuntimeError("MCP response missing Content-Length")
    body_start = header_end + 4
    body_end = body_start + content_length
    if len(buffer) < body_end:
        raise RuntimeError("MCP response body truncated")
    return json.loads(buffer[body_start:body_end].decode("utf-8")), buffer[body_end:]


def send_message(proc: subprocess.Popen[bytes], payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    packet = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(packet)
    proc.stdin.flush()

    buffer = b""
    while True:
        chunk = proc.stdout.read1(4096)
        if not chunk:
            raise RuntimeError("MCP server closed stdout unexpectedly")
        buffer += chunk
        try:
            message, _ = extract_message(buffer)
            return message
        except RuntimeError:
            continue


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        original_index = (ROOT / "knowledge_base" / "index.json").read_text(encoding="utf-8")
        input_path = Path(tmp_dir) / "conversation.json"
        input_path.write_text(
            json.dumps(
                {
                    "messages": [
                        {"role": "user", "content": "請建立知識庫匯出流程"},
                        {"role": "assistant", "content": "已補上 search 與 read 工具"},
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        export_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "export_conversation.py"),
            "--input",
            str(input_path),
            "--source",
            "smoke",
            "--title",
            "Knowledge Base Smoke",
            "--summary",
            "knowledge base smoke summary",
            "--tags",
            "codex",
            "mcp",
        ]
        export_payload = json.loads(subprocess.check_output(export_cmd, cwd=ROOT, text=True))
        entry_path = ROOT / export_payload["json"]
        markdown_path = ROOT / export_payload["markdown"]
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        entry_id = entry["id"]

        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "mcp_server" / "knowledge_base_server.py")],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            initialize = send_message(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1.0"}},
                },
            )
            if initialize.get("result", {}).get("protocolVersion") != "2024-11-05":
                raise RuntimeError("initialize protocol version mismatch")

            tool_list = send_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            tools = tool_list.get("result", {}).get("tools", [])
            tool_names = {tool.get("name") for tool in tools}
            if {"search", "read"} - tool_names:
                raise RuntimeError("tools/list missing search/read")

            search_result = send_message(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "search", "arguments": {"query": "knowledge base smoke", "limit": 5}},
                },
            )
            search_content = search_result.get("result", {}).get("content", [])
            if not search_content:
                raise RuntimeError("search returned no content")
            search_payload = json.loads(search_content[0]["text"])
            result_ids = {item["id"] for item in search_payload.get("results", [])}
            if entry_id not in result_ids:
                raise RuntimeError("search did not return exported entry")

            read_result = send_message(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "read", "arguments": {"id": entry_id}},
                },
            )
            read_content = read_result.get("result", {}).get("content", [])
            if not read_content:
                raise RuntimeError("read returned no content")
            read_payload = json.loads(read_content[0]["text"])
            if read_payload.get("summary") != "knowledge base smoke summary":
                raise RuntimeError("read payload summary mismatch")
        finally:
            proc.terminate()
            proc.communicate(timeout=5)
            entry_path.unlink(missing_ok=True)
            markdown_path.unlink(missing_ok=True)
            (ROOT / "knowledge_base" / "index.json").write_text(original_index, encoding="utf-8")

    print("knowledge base mcp smoke passed: export + search + read + protocol")


if __name__ == "__main__":
    main()
