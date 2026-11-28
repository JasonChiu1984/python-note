"""REST 用戶端：分頁讀取、429／503 依 Retry-After 退避、非冪等請求不自動重試（標準函式庫）。

程式在本機啟動一個模擬設備清冊 API（127.0.0.1 隨機埠），用 urllib 呼叫它。
等待時間記錄下來而不是真的 sleep，讓輸出可重現。
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEVICES = [{"id": f"AHU-{i:02d}", "status": "running" if i % 4 else "alarm"} for i in range(1, 12)]
STATE = {"calls": 0}


class Api(BaseHTTPRequestHandler):
    def log_message(self, *args):          # 不把存取紀錄印到輸出
        pass

    def _json(self, code, body, headers=()):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in headers:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        STATE["calls"] += 1
        if STATE["calls"] in (2, 3):        # 第 2、3 次呼叫模擬限流與維護
            code = 429 if STATE["calls"] == 2 else 503
            return self._json(code, {"error": "busy"}, [("Retry-After", "2")])
        q = parse_qs(urlparse(self.path).query)
        offset, limit = int(q.get("offset", ["0"])[0]), int(q.get("limit", ["5"])[0])
        page = DEVICES[offset:offset + limit]
        nxt = offset + limit if offset + limit < len(DEVICES) else None
        self._json(200, {"items": page, "next_offset": nxt})

    def do_POST(self):
        self._json(503, {"error": "maintenance"}, [("Retry-After", "5")])


def retry_after_seconds(value, now, fallback):
    if value is None:
        return fallback
    value = value.strip()
    if value.isascii() and value.isdecimal():
        return int(value)
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            return fallback
        return max(0.0, (when - now).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return fallback


def request(method, url, body=None, *, waits, max_attempts=4, max_wait=30):
    idempotent = method in ("GET", "HEAD", "PUT", "DELETE")
    # 只用於本機模擬；不繼承系統代理設定。
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(url, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=5) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            with e:
                if e.code not in (429, 503) or not idempotent or attempt == max_attempts:
                    raise
                delay = retry_after_seconds(e.headers.get("Retry-After"),
                                            datetime.now(timezone.utc), min(2**(attempt - 1), max_wait))
                if delay > max_wait:
                    raise  # 不在伺服器要求的時間之前重送：停止，交由排程延後。
                waits.append((e.code, delay))  # 模擬：正式客戶端需真的等待。


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), Api)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/devices"

    waits, items, offset = [], [], 0
    while offset is not None:
        page = request("GET", f"{base}?offset={offset}&limit=5", waits=waits)
        items += page["items"]
        offset = page["next_offset"]
    print(f"共讀到 {len(items)} 台設備，告警中：{[d['id'] for d in items if d['status'] == 'alarm']}")
    print(f"重試紀錄（狀態碼, 等待秒數）：{waits}")
    print(f"伺服器實際收到 GET 次數：{STATE['calls']}")

    try:
        request("POST", base, {"id": "AHU-12"}, waits=waits)
    except urllib.error.HTTPError as e:
        print(f"POST 收到 {e.code}，Retry-After={e.headers['Retry-After']}；非冪等請求不自動重試，交由使用者確認")
    server.shutdown()
    server.server_close()
