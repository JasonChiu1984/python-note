"""只對程式自行建立的 127.0.0.1 fixture 做有限 GET。Python 3.10+。"""
import argparse
import http.client
import json
import time
import unittest
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.robotparser import RobotFileParser

AGENT = "HVACLab"
PATHS = ("/catalog", "/detail/a", "/detail/b", "/blocked", "/api")
ROBOTS = b"User-agent: *\nDisallow: /blocked\n"
LIMIT, MAX_BODY = 8, 16_384


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.hits[self.path] += 1
        if self.path == "/detail/b" and self.server.hits[self.path] <= 1:
            self.send_response(429)
            self.send_header("Retry-After", "1")
            self.end_headers()
            return
        content = {
            "/robots.txt": ("text/plain", ROBOTS.decode()),
            "/catalog": ("text/html", """<a href="/detail/a">A</a>
                <a href="/detail/a">A copy</a><a href="/detail/b">B</a>
                <a href="/blocked">blocked</a><a href="https://example.invalid/">external</a>"""),
            "/detail/a": ("text/html", '<article data-id="AHU-A" data-value="25.5"></article>'),
            "/detail/b": ("text/html", '<article data-id="AHU-B" data-value="24.8"></article>'),
            "/api": ("application/json", '{"items":[{"id":"AHU-A","temperature_c":"25.5"}]}'),
        }.get(self.path)
        if content is None:
            self.send_error(404)
            return
        mime, payload = content
        body = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def fixture():
    with HTTPServer(("127.0.0.1", 0), Fixture) as server:
        server.hits = Counter()
        thread = Thread(target=server.serve_forever,
                        kwargs={"poll_interval": .02}, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join()


class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.rows = [], []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])
        if tag == "article" and data.get("data-id") and data.get("data-value"):
            self.rows.append({"id": data["data-id"], "temperature_c": data["data-value"]})


def parse_html(text):
    p = Extract()
    p.feed(text)
    p.close()
    return p


def retry_delay(value, now):
    """RFC 9110 的秒數或 HTTP 日期；無效值使用保守預設 1 秒。"""
    if value and value.isascii() and value.isdigit():
        # 大到不必轉整數，直接交給呼叫端判斷超出預算。
        digits = value.lstrip("0") or "0"
        return int(digits) if len(digits) <= 3 else float("inf")
    if value:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is not None:
                return max(0, (parsed - now).total_seconds())
        except (ValueError, TypeError, OverflowError):
            pass
    return 1


class Client:
    def __init__(self, port, sleep=time.sleep, monotonic=time.monotonic):
        self.port = port
        self.sleep, self.clock = sleep, monotonic
        self.requests, self.retries, self.next_at = 0, 0, 0

    def get(self, path, expected):
        if path not in (*PATHS, "/robots.txt"):
            raise ValueError("不在本機 fixture 白名單")
        for attempt in range(2):  # 首次加最多一次重試
            if self.requests >= LIMIT:
                raise RuntimeError("全域請求預算用完")
            wait = self.next_at - self.clock()
            if wait > 0:
                self.sleep(wait)
            self.requests += 1
            self.next_at = self.clock() + .15
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
            try:
                conn.request("GET", path, headers={"User-Agent": AGENT})
                response = conn.getresponse()
                if response.status == 429 and attempt == 0:
                    delay = retry_delay(response.getheader("Retry-After"),
                                        datetime.now(timezone.utc))
                    if delay > 2:
                        raise RuntimeError("Retry-After 超出等待預算；停止，不提早重試")
                    self.retries += 1
                    self.next_at = max(self.next_at, self.clock() + delay)
                    continue
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}：不跟隨轉址")
                mime = (response.getheader("Content-Type") or "").split(";")[0].strip()
                if mime != expected:
                    raise RuntimeError("內容類型與預期不符")
                body = response.read(MAX_BODY + 1)
                if len(body) > MAX_BODY:
                    raise RuntimeError("回應超出大小上限")
                return body.decode("utf-8")
            finally:
                conn.close()
        raise AssertionError("迴圈應回傳或拋出例外")


def collect(client, mode):
    if mode not in ("html", "api"):
        raise ValueError("未知來源模式")
    # 標準函式庫只示範 fixture 內簡單規則，不聲稱完整實作 RFC 9309。
    robots = RobotFileParser()
    robots.parse(client.get("/robots.txt", "text/plain").splitlines())

    def fetch(path, mime):
        if not robots.can_fetch(AGENT, path):
            raise RuntimeError("robots 規則拒絕根路徑")
        return client.get(path, mime)

    counts = Counter()
    rows = {}
    if mode == "api":
        for row in json.loads(fetch("/api", "application/json"))["items"]:
            rows.setdefault(row["id"], row)
    else:
        index = parse_html(fetch("/catalog", "text/html"))
        visited = set()
        for path in index.links:
            counts["candidates"] += 1
            if path not in PATHS[1:4]:
                counts["out_of_scope"] += 1
            elif path in visited:
                counts["duplicate"] += 1
            elif not robots.can_fetch(AGENT, path):
                counts["robots_skips"] += 1
            else:
                visited.add(path)
                for row in parse_html(fetch(path, "text/html")).rows:
                    rows.setdefault(row["id"], row)
    return {"items": list(rows.values()), "decisions": dict(counts),
            "requests": client.requests, "retries": client.retries}


class VirtualClock:
    def __init__(self):
        self.now = 0

    def tick(self, seconds):
        self.now += seconds


class Tests(unittest.TestCase):
    def test_html(self):
        timer = VirtualClock()
        with fixture() as server:
            result = collect(Client(server.server_port, timer.tick, lambda: timer.now), "html")
            self.assertEqual(result["requests"], 5)
            self.assertEqual(result["retries"], 1)
            self.assertEqual(len(result["items"]), 2)
            self.assertEqual(server.hits["/blocked"], 0)
            self.assertEqual(server.hits["/detail/a"], 1)
            self.assertEqual(result["decisions"], {"candidates": 5, "out_of_scope": 1,
                                                  "duplicate": 1, "robots_skips": 1})
            self.assertGreaterEqual(timer.now, 1.45)

    def test_api(self):
        with fixture() as server:
            result = collect(Client(server.server_port, lambda _: None), "api")
            self.assertEqual(result["items"][0]["id"], "AHU-A")
            self.assertEqual(result["requests"], 2)

    def test_retry_delay(self):
        now = datetime(2026, 11, 25, tzinfo=timezone.utc)
        self.assertEqual(retry_delay("2", now), 2)
        self.assertEqual(retry_delay("Wed, 25 Nov 2026 00:00:02 GMT", now), 2)
        self.assertEqual(retry_delay("bogus", now), 1)
        self.assertGreater(retry_delay("1000", now), 2)

    def test_out_of_scope(self):
        with self.assertRaises(ValueError):
            Client(1).get("http://example.invalid/a", "text/html")

    def test_budget(self):
        client = Client(1)
        client.requests = LIMIT
        with self.assertRaisesRegex(RuntimeError, "預算"):
            client.get("/catalog", "text/html")

    def test_mime(self):
        with fixture() as server:
            with self.assertRaisesRegex(RuntimeError, "內容類型"):
                Client(server.server_port).get("/api", "text/html")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("html", "api", "self-test"))
    mode = p.parse_args().mode
    if mode == "self-test":
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    with fixture() as server:
        print(json.dumps(collect(Client(server.server_port), mode),
                         indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
