import io
import json
import subprocess
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

import app
import host


class InteropTests(unittest.TestCase):
    def test_process_output(self):
        with patch("sys.argv", ["app.py", "sample"]), patch("sys.stdout", new_callable=io.StringIO) as out:
            app.main()
        self.assertEqual(json.loads(out.getvalue()), app.SAMPLE)

    def test_status_parses_array_lines_and_empty(self):
        outputs = [('[{"State":"running"}]', 1), ('{"State":"running"}\n{"State":"exited"}', 2), ('', 0)]
        for raw, size in outputs:
            with self.subTest(raw=raw), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, raw, "")) as run:
                self.assertEqual(len(host.compose_status("reviewed-local")), size)
                args = run.call_args.args[0]
                self.assertEqual(args[:4], ["docker", "--context", "reviewed-local", "compose"])
                self.assertTrue(run.call_args.kwargs["check"])
                self.assertEqual(run.call_args.kwargs["timeout"], 8)

    def test_status_propagates_cli_failure(self):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(126, ["docker"])):
            with self.assertRaises(subprocess.CalledProcessError):
                host.compose_status("reviewed-local")

    def test_http_data_plane(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), app.Handler) as server:
            worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(f"{base}/healthz", timeout=2) as response:
                    self.assertEqual(json.load(response), {"status": "ok"})
                self.assertEqual(host.sample(f"{base}/sample"), app.SAMPLE)
                with self.assertRaises(ValueError):
                    host.sample(f"{base}/healthz")
                with self.assertRaises(HTTPError) as error:
                    host.sample(f"{base}/wrong")
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()  # 與 serve_forever 不在同一執行緒。
                worker.join(timeout=2)
                self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
