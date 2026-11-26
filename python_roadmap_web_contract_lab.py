"""Web 路線的四種契約，完全離線：不擷取網頁、不連接服務。"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from html import escape
import re
import unittest


def create_app():
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel

    class Telemetry(BaseModel):
        device: str
        version: int

    @asynccontextmanager
    async def lifespan(app):
        app.state.snapshot = {"device": "CH-01", "version": 7, "internal": "private"}
        try:
            yield
        finally:
            del app.state.snapshot

    app = FastAPI(lifespan=lifespan)

    @app.get("/telemetry/{device}", response_model=Telemetry)
    async def read(device: str, request: Request):
        data = request.app.state.snapshot
        if device != data["device"]:
            raise HTTPException(404, "device not found")
        return data

    return app


@dataclass(frozen=True)
class Message:
    stream: str
    seq: int
    value: str


def merge(current, incoming, *, snapshot=False):
    """此模型每個 stream 內連號；重啟換 stream 必須經過可信快照。"""
    if type(incoming.seq) is not int or incoming.seq < 0 or not incoming.stream:
        raise ValueError("invalid event")
    if current is not None and incoming.stream == current.stream:
        if incoming.seq <= current.seq:
            return "ignore", current
        if snapshot or incoming.seq == current.seq + 1:
            return "apply", incoming
    elif snapshot:
        return "apply", incoming
    return "resync", current


def retry_delay(*, status, idempotent, remaining_ms, jitter_ms, retry_after_ms=None):
    """已正規化成毫秒的政策輸入；不是 HTTP client。"""
    if min(remaining_ms, jitter_ms) < 0 or (retry_after_ms is not None and retry_after_ms < 0):
        raise ValueError("negative time")
    if not idempotent or status not in (429, 502, 503, 504):
        return None
    # 預留下一次嘗試至少 50ms；不把伺服器指定等待縮短到預算內。
    delay = max(jitter_ms, retry_after_ms or 0)
    return delay if delay + 50 <= remaining_ms else None


DEVICE = re.compile(r"[A-Z]{2}-[0-9]{2}")
FIXTURE = '<main><article data-device="CH-01"><h2> 並聯 冰機 </h2></article></main>'


def extract(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    for article in soup.select("main article[data-device]"):
        key = article.get("data-device")
        heading = article.select_one("h2")
        if not isinstance(key, str) or not DEVICE.fullmatch(key) or key in seen or heading is None:
            raise ValueError("source schema changed")
        text = heading.get_text(" ", strip=True)
        if not text:
            raise ValueError("empty heading")
        seen.add(key)
        yield key, text
    if not seen:
        raise ValueError("no records; check the fixture or selector")


class LabTests(unittest.TestCase):
    def test_fastapi_contract_and_shutdown(self):
        from fastapi.testclient import TestClient

        app = create_app()
        with TestClient(app) as client:
            self.assertEqual(client.get("/telemetry/CH-01").json(), {"device": "CH-01", "version": 7})
            self.assertEqual(client.get("/telemetry/XX-01").status_code, 404)
            self.assertEqual(set(app.openapi()["components"]["schemas"]["Telemetry"]["properties"]),
                             {"device", "version"})
        self.assertFalse(hasattr(app.state, "snapshot"))

    def test_stream(self):
        start = Message("boot-1", 5, "normal")
        self.assertEqual(merge(None, start), ("resync", None))
        self.assertEqual(merge(None, start, snapshot=True), ("apply", start))
        self.assertEqual(merge(start, Message("boot-1", 5, "old")), ("ignore", start))
        self.assertEqual(merge(start, Message("boot-1", 7, "gap")), ("resync", start))
        self.assertEqual(merge(start, Message("boot-2", 1, "reset")), ("resync", start))
        current = Message("boot-1", 6, "new")
        self.assertEqual(merge(start, current), ("apply", current))

    def test_retry(self):
        for status, safe, budget, hint, result in [
            (503, True, 180, 100, 100), (429, True, 120, 100, None),
            (503, False, 180, None, None), (403, True, 180, None, None),
            (504, True, 80, None, 30),
        ]:
            self.assertEqual(retry_delay(status=status, idempotent=safe, remaining_ms=budget,
                                         jitter_ms=30, retry_after_ms=hint), result)

    def test_parser(self):
        self.assertEqual(list(extract(FIXTURE)), [("CH-01", "並聯 冰機")])
        for invalid in ("<main></main>", FIXTURE.replace("CH-01", "CH-01X"),
                        FIXTURE.replace("<h2>", "<h3>").replace("</h2>", "</h3>"),
                        FIXTURE.replace("</main>", '<article data-device="CH-01"><h2>x</h2></article></main>')):
            with self.assertRaises(ValueError):
                list(extract(invalid))
        markup = FIXTURE.replace("並聯 冰機", escape("<b>原始文字</b>"))
        self.assertEqual(list(extract(markup))[0][1], "<b>原始文字</b>")


if __name__ == "__main__":
    unittest.main(verbosity=2)
