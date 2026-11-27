"""Loopback-only regression, execution does not require Docker."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from app import Handler
from bench_http import measure, quantile


class BenchmarkTests(unittest.TestCase):
    def test_nearest_rank(self):
        self.assertEqual(quantile([30, 2, 7, 50], .50), 7)
        self.assertEqual(quantile([30, 2, 7, 50], .95), 50)
        self.assertIsNone(quantile([], .99))

    def test_reject_invalid_parameters(self):
        with self.assertRaises(ValueError):
            measure(8080, 9, 1, 0)

    def test_actual_loopback_cli_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as temp, ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            out = Path(temp) / "trial.csv"
            worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02})
            worker.start()
            cmd = [sys.executable, str(Path(__file__).with_name("bench_http.py")),
                   "--port", str(server.server_port), "--workers", "2", "--count", "4",
                   "--warmup", "2", "--csv", str(out)]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=8)
                report = json.loads(result.stdout)
                self.assertEqual((report["attempts"], report["success"], report["failures"]), (4, 4, 0))
                saved = out.read_text()
                self.assertEqual(len(saved.splitlines()), 5)
                self.assertNotEqual(subprocess.run(cmd, capture_output=True, timeout=8).returncode, 0)
                self.assertEqual(out.read_text(), saved)
            finally:
                server.shutdown()
                worker.join(timeout=2)

    def test_bad_payload_is_counted_not_an_http_success(self):
        class WrongHandler(Handler):
            def do_GET(self):
                self.path = "/healthz"
                return super().do_GET()

        with ThreadingHTTPServer(("127.0.0.1", 0), WrongHandler) as server:
            worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02})
            worker.start()
            try:
                rows, result = measure(server.server_port, 1, 2, 0)
                self.assertEqual([r[3:] for r in rows], [(200, "contract"), (200, "contract")])
                self.assertEqual(result["failure_ratio"], 1)
                self.assertIsNone(result["p99_ms_success_only"])
            finally:
                server.shutdown()
                worker.join(timeout=2)
