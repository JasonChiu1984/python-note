"""Small HTTP service exposing health and readiness endpoints."""

from __future__ import annotations

import json
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Condition
from typing import Any

from .config import ConfigError, RuntimeConfig, load_config
from .health import RuntimeState, health_report, readiness_report
from .logging_utils import log_json


class RuntimeHandler(BaseHTTPRequestHandler):
    config: RuntimeConfig
    state: RuntimeState

    def log_message(self, format: str, *args: Any) -> None:
        log_json("http_access", path=self.path, client=self.client_address[0], message=format % args)

    def _send_json(self, status_code: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            status_code, payload = health_report(self.config, self.state)
        elif self.path == "/readyz":
            status_code, payload = readiness_report(self.config, self.state)
        else:
            status_code, payload = 404, {"status": "not_found", "path": self.path}
        self._send_json(status_code, payload)


class RuntimeServer(ThreadingHTTPServer):
    # Request workers cannot keep the process alive beyond the drain deadline.
    daemon_threads = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._idle = Condition()
        self._active = 0
        super().__init__(*args, **kwargs)
        self.timeout = 0.1

    def process_request(self, request: Any, client_address: Any) -> None:
        with self._idle:
            self._active += 1
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_finished()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_finished()

    def _request_finished(self) -> None:
        with self._idle:
            self._active -= 1
            self._idle.notify_all()

    def drain(self, timeout: float) -> bool:
        with self._idle:
            return self._idle.wait_for(lambda: self._active == 0, timeout=timeout)


def build_server(config: RuntimeConfig, state: RuntimeState) -> RuntimeServer:
    RuntimeHandler.config = config
    RuntimeHandler.state = state
    return RuntimeServer((config.host, config.port), RuntimeHandler)


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        log_json("config_error", error=str(exc))
        return 2

    state = RuntimeState.started_now()
    server = build_server(config, state)
    stop_signal = None

    def record_signal(signum: int, _frame: object) -> None:
        nonlocal stop_signal
        # No logging, locks or blocking shutdown calls inside a signal handler.
        if stop_signal is None:
            stop_signal = signum

    try:
        signal.signal(signal.SIGTERM, record_signal)
        signal.signal(signal.SIGINT, record_signal)
        log_json("service_started", service=config.app_name, port=config.port, environment=config.environment)
        while stop_signal is None:
            server.handle_request()
        state.mark_draining()
        log_json("shutdown_requested", signal=stop_signal)
    finally:
        server.server_close()

    drained = server.drain(config.shutdown_timeout_seconds)
    if not drained:
        log_json("shutdown_timed_out", timeout_seconds=config.shutdown_timeout_seconds)
    log_json("service_stopped", service=config.app_name, drained=drained)
    return 0 if drained else 1


if __name__ == "__main__":
    raise SystemExit(main())
