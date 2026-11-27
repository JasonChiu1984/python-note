"""不靠 SDK，用標準函式庫組出 MCP 2026-07-28 的請求並驗證回應結構（只做格式練習，不連線）。

重點：沒有 initialize 握手；每個請求的 params._meta 都帶協定版本與 client 能力；
HTTP 傳輸時標頭 MCP-Protocol-Version、Mcp-Method、Mcp-Name 要與本文一致。
"""
import json

PROTOCOL = "2026-07-28"
META = {"io.modelcontextprotocol/protocolVersion": PROTOCOL,
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "bms-checker", "version": "1.0"}}


def request(rid, method, params=None, name=None):
    body = {"jsonrpc": "2.0", "id": rid, "method": method, "params": {**(params or {}), "_meta": META}}
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": PROTOCOL, "Mcp-Method": method}
    if name:
        headers["Mcp-Name"] = name
    return headers, body


def check_headers(headers, body):
    problems = []
    if headers.get("MCP-Protocol-Version") != body["params"]["_meta"].get("io.modelcontextprotocol/protocolVersion"):
        problems.append("MCP-Protocol-Version 與 _meta 不一致（HeaderMismatch -32020）")
    if headers.get("Mcp-Method") != body["method"]:
        problems.append("Mcp-Method 與 method 不一致")
    if body["method"] == "tools/call" and headers.get("Mcp-Name") != body["params"].get("name"):
        problems.append("Mcp-Name 與工具名稱不一致")
    return problems or ["OK"]


def check_result(resp):
    r = resp.get("result", {})
    missing = [k for k in ("resultType",) if k not in r]
    if resp.get("error", {}).get("code") == -32022:
        return f"UnsupportedProtocolVersion，伺服器支援 {resp['error']['data']['supported']}"
    return "結構正確" if not missing else f"缺少 {missing}"


if __name__ == "__main__":
    h, b = request(1, "server/discover")
    print("discover 本文：", json.dumps(b, ensure_ascii=False)[:120], "…")
    h, b = request(2, "tools/call", {"name": "search_notes", "arguments": {"query": "Pump"}}, name="search_notes")
    print("tools/call 標頭：", {k: v for k, v in h.items() if k.startswith(("MCP", "Mcp"))})
    print("一致性檢查：", check_headers(h, b))
    h["Mcp-Name"] = "delete_notes"
    print("標頭被改過：", check_headers(h, b))
    print("回應檢查：", check_result({"jsonrpc": "2.0", "id": 2, "result": {"resultType": "complete", "content": []}}))
    print("回應檢查：", check_result({"jsonrpc": "2.0", "id": 3, "error": {"code": -32022, "message": "Unsupported protocol version",
                                         "data": {"supported": ["2025-11-25"], "requested": PROTOCOL}}}))
    print("舊版回應（無 resultType）依規格視為 complete，但新版伺服器必須提供：", check_result({"result": {"content": []}}))
