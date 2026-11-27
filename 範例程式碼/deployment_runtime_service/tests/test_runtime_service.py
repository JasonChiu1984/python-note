from pathlib import Path
import json
import os
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
from urllib.request import urlopen

from deployment_runtime_service.config import ConfigError, load_config
from deployment_runtime_service.deployment_contract import validate_deployment_files
from deployment_runtime_service.health import RuntimeState, health_report, readiness_report
from deployment_runtime_service.logging_utils import log_json, redact


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeConfigTests(unittest.TestCase):
    def test_load_config_from_environment_mapping(self) -> None:
        config = load_config({
            "APP_NAME": "runtime-demo",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "8090",
            "APP_ENV": "test",
            "DEPENDENCY_STATUS": "healthy",
            "SHUTDOWN_TIMEOUT_SECONDS": "5",
        })

        self.assertEqual(config.app_name, "runtime-demo")
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8090)
        self.assertEqual(config.environment, "test")

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            load_config({"APP_PORT": "70000"})

    def test_shutdown_timeout_must_be_finite_and_positive(self) -> None:
        for raw in ("0", "-1", "nan", "inf", "1e50"):
            with self.subTest(value=raw), self.assertRaises(ConfigError):
                load_config({"SHUTDOWN_TIMEOUT_SECONDS": raw})


class HealthContractTests(unittest.TestCase):
    def test_health_stays_ok_when_dependency_is_degraded(self) -> None:
        config = load_config({"DEPENDENCY_STATUS": "degraded"})
        status_code, payload = health_report(config, RuntimeState.started_now())

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")

    def test_readiness_fails_when_dependency_is_degraded(self) -> None:
        config = load_config({"DEPENDENCY_STATUS": "degraded"})
        status_code, payload = readiness_report(config, RuntimeState.started_now())

        self.assertEqual(status_code, 503)
        self.assertEqual(payload["status"], "not_ready")

    def test_readiness_fails_while_draining(self) -> None:
        config = load_config({"DEPENDENCY_STATUS": "healthy"})
        state = RuntimeState.started_now()
        state.mark_draining()

        status_code, payload = readiness_report(config, state)

        self.assertEqual(status_code, 503)
        self.assertEqual(payload["reason"], "service is draining")


class LoggingTests(unittest.TestCase):
    def test_redact_sensitive_values(self) -> None:
        payload = redact({"user": "operator", "token": "plain-secret"})

        self.assertEqual(payload["user"], "operator")
        self.assertEqual(payload["token"], "***")

    def test_log_json_returns_parseable_json(self) -> None:
        line = log_json("test_event", token="plain-secret", request_id="abc")
        payload = json.loads(line)

        self.assertEqual(payload["event"], "test_event")
        self.assertEqual(payload["token"], "***")


class DeploymentContractTests(unittest.TestCase):
    def test_deployment_files_contain_required_runtime_contracts(self) -> None:
        missing = validate_deployment_files(PROJECT_ROOT)

        self.assertEqual(missing, {"Dockerfile": [], "compose.yaml": [], ".dockerignore": []})


@unittest.skipUnless(os.name == "posix", "POSIX signal delivery required")
class ProcessLifecycleTests(unittest.TestCase):
    def test_exit_after_normal_stop_signals(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig):
                self._exercise(sig)

    def test_existing_request_finishes_before_exit(self) -> None:
        self._exercise(signal.SIGTERM, hold=True)

    def test_over_budget_request_is_not_reported_as_drained(self) -> None:
        self._exercise(signal.SIGTERM, hold=True, expire=True)

    def _exercise(self, sig: signal.Signals, *, hold: bool = False, expire: bool = False) -> None:
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        env = dict(os.environ, PYTHONPATH=str(PROJECT_ROOT / "src"),
                   APP_HOST="127.0.0.1", APP_PORT=str(port), DEPENDENCY_STATUS="healthy",
                   SHUTDOWN_TIMEOUT_SECONDS="0.2" if expire else "5")
        args = [sys.executable, "-u", "-m", "deployment_runtime_service.server"]
        if hold:
            # Only the synthetic handler is replaced. main() still owns the real
            # listener, POSIX signal handler, deadline and exit status.
            args = [sys.executable, "-u", "-c", """
import os
import sys
from deployment_runtime_service import server
original = server.RuntimeHandler.do_GET
def get(self):
    if self.path != "/hold":
        return original(self)
    server.log_json("test_entered")
    os.read(sys.stdin.fileno(), 1)
    self._send_json(200, {"status": "finished"})
    server.log_json("test_finished")
server.RuntimeHandler.do_GET = get
raise SystemExit(server.main())
"""]
        with subprocess.Popen(args, env=env, text=True, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
            assert child.stdout is not None and child.stdin is not None
            messages: queue.Queue[dict] = queue.Queue()
            def collect() -> None:
                for line in child.stdout:
                    messages.put(json.loads(line))
            reader = threading.Thread(target=collect, daemon=True)
            reader.start()
            events = []
            def wait_event(event: str) -> dict:
                until = time.monotonic() + 5
                while time.monotonic() < until:
                    try:
                        row = messages.get(timeout=max(0, until - time.monotonic()))
                    except queue.Empty:
                        break
                    events.append(row["event"])
                    if row["event"] == event:
                        return row
                self.fail(f"missing {event}; logged {events!r}")
            pending = None
            try:
                wait_event("service_started")
                with urlopen(f"http://127.0.0.1:{port}/readyz", timeout=2) as r:
                    self.assertEqual(r.status, 200)
                wait_event("http_access")
                if hold:
                    pending = socket.create_connection(("127.0.0.1", port), timeout=3)
                    pending.sendall(b"GET /hold HTTP/1.0\r\nHost: localhost\r\n\r\n")
                    wait_event("test_entered")
                child.send_signal(sig)
                self.assertEqual(wait_event("shutdown_requested")["signal"], sig)
                if hold and not expire:
                    self.assertIsNone(child.poll(), "exited while request was held")
                    child.stdin.write("\n")
                    child.stdin.flush()
                    wait_event("test_finished")
                    assert pending is not None
                    with pending.makefile("rb") as stream:
                        first = stream.readline()
                        self.assertIn(b" 200 ", first)
                        self.assertIn(b'"finished"', stream.read())
                if expire:
                    self.assertEqual(wait_event("shutdown_timed_out")["timeout_seconds"], .2)
                self.assertIs(wait_event("service_stopped")["drained"], not expire)
                self.assertEqual(child.wait(timeout=5), 1 if expire else 0)
                reader.join(timeout=2)
                rest = []
                while not messages.empty():
                    rest.append(messages.get_nowait()["event"])
                self.assertEqual((events + rest).count("shutdown_requested"), 1)
                self.assertEqual((events + rest).count("service_stopped"), 1)
            finally:
                if pending is not None:
                    pending.close()
                if child.poll() is None:
                    child.kill()
                child.wait()
                reader.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
