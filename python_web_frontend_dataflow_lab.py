"""Loopback-only synthetic API. Python 3.10+. No packages, devices or real data."""
import argparse
import json
import math
import threading
import time
import unittest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

PAGE = Path(__file__).with_name("python_web_frontend_dataflow_tutorial.html")
ZONES = ("AHU-01", "AHU-02", "CH-01")


def readings(now):
    return [
        {"device": device, "temperature_c": round(23 + i + math.sin(now / 8 + i) * 1.8, 1),
         "unit": "°C", "quality": "good", "sampled_at_unix": now}
        for i, device in enumerate(ZONES)
    ]


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def respond(self, status, payload, mime="application/json; charset=utf-8"):
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A canceled client may already have closed the socket.

    def error_json(self, status, code, message):
        self.respond(status, {"error": {"code": code, "message": message}})

    def trusted_host(self):
        expected = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected:
            self.error_json(400, "invalid_host", "Use the displayed loopback address.")
            return False
        return True

    def do_GET(self):
        if not self.trusted_host():
            return
        parsed = urlsplit(self.path)
        if parsed.path in ("/", f"/{PAGE.name}"):
            try:
                body = PAGE.read_bytes().replace(
                    b'data-transport="demo"', b'data-transport="http"', 1)
            except FileNotFoundError:
                self.error_json(404, "missing_page", "Put HTML next to this Python file.")
                return
            self.respond(200, body, "text/html; charset=utf-8")
        elif parsed.path == f"/{Path(__file__).name}":
            self.respond(200, Path(__file__).read_bytes(), "text/plain; charset=utf-8")
        elif parsed.path == "/api/v1/telemetry":
            try:
                params = parse_qs(parsed.query, max_num_fields=4, keep_blank_values=True)
                if not set(params) <= {"delay_ms", "device"} or any(len(v) != 1 for v in params.values()):
                    raise ValueError
                delay = int(params.get("delay_ms", ["0"])[0])
                device = params.get("device", [""])[0]
                if delay < 0 or delay > 3000 or (device and device not in ZONES):
                    raise ValueError
            except ValueError:
                self.error_json(400, "invalid_query", "Check device and delay_ms (0–3000).")
                return
            if delay:
                time.sleep(delay / 1000)
            now = int(time.time())
            items = readings(now)
            if device:
                items = [x for x in items if x["device"] == device]
            self.respond(200, {"schema_version": 1, "simulated": True, "items": items})
        else:
            self.error_json(404, "not_found", "No route matches this URL.")

    def do_POST(self):
        if not self.trusted_host():
            return
        if urlsplit(self.path).path != "/api/v1/threshold-preview":
            self.error_json(404, "not_found", "No route matches this URL.")
            return
        # Ordinary CLI clients send no Origin. Browsers from other origins are rejected.
        origin = self.headers.get("Origin")
        if origin is not None and origin != f"http://127.0.0.1:{self.server.server_port}":
            self.error_json(403, "origin_denied", "Browser origin is not the lab origin.")
            return
        if self.headers.get_content_type() != "application/json":
            self.error_json(415, "unsupported_media_type", "Send application/json.")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.error_json(411, "length_required", "Send Content-Length.")
            return
        if not 0 < length <= 2048:
            self.error_json(413, "body_size", "Body must be between 1 and 2048 bytes.")
            return
        try:
            obj = json.loads(self.rfile.read(length))
            if not isinstance(obj, dict) or set(obj) != {"threshold_c"}:
                raise ValueError
            value = obj["threshold_c"]
            if type(value) not in (int, float) or not 0 <= value <= 60:
                raise ValueError
        except (ValueError, UnicodeError, TimeoutError):
            self.error_json(400, "invalid_body", "threshold_c must be a number from 0 to 60.")
            return
        now = int(time.time())
        at_or_above = [x["device"] for x in readings(now) if x["temperature_c"] >= value]
        self.respond(200, {"threshold_c": value, "at_or_above": at_or_above, "persisted": False})

class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path, body=None, headers=None):
        req = Request(self.base + path, data=body, headers=headers or {})
        try:
            response = urlopen(req, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            data = json.loads(raw) if response.headers.get_content_type() == "application/json" else raw
            return response.status, data

    def test_entry_page(self):
        status, body = self.get("/")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn(b"/api/v1/telemetry", body)

    def test_telemetry_and_filter(self):
        status, body = self.get("/api/v1/telemetry?device=AHU-02")
        self.assertEqual(status, 200)
        self.assertEqual([x["device"] for x in body["items"]], ["AHU-02"])
        self.assertTrue(body["simulated"])

    def test_bad_query_and_route(self):
        self.assertEqual(self.get("/api/v1/telemetry?delay_ms=3001")[0], 400)
        self.assertEqual(self.get("/missing")[0], 404)

    def test_preview(self):
        status, body = self.get("/api/v1/threshold-preview", b'{"threshold_c":0}',
                                {"Content-Type": "application/json", "Origin": self.base})
        self.assertEqual(status, 200)
        self.assertEqual(body["at_or_above"], list(ZONES))
        self.assertIs(body["persisted"], False)

    def test_preview_rejected(self):
        path = "/api/v1/threshold-preview"
        self.assertEqual(self.get(path, b'{"threshold_c":0}', {"Content-Type": "application/json",
                            "Origin": "https://invalid.example"})[0], 403)
        self.assertEqual(self.get(path, b"invalid", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.get(path, b"{}", {"Content-Type": "text/plain"})[0], 415)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        unittest.main(argv=["python_web_frontend_dataflow_lab.py"], verbosity=2)
    else:
        with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
            print(f"Open http://127.0.0.1:{server.server_port}/ (Ctrl+C to stop)", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
