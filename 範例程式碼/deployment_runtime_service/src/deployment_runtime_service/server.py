"""Small HTTP service exposing health and readiness endpoints."""

from __future__ import annotations

import json
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def build_server(config: RuntimeConfig, state: RuntimeState) -> ThreadingHTTPServer:
    RuntimeHandler.config = config
    RuntimeHandler.state = state
    return ThreadingHTTPServer((config.host, config.port), RuntimeHandler)


def install_signal_handlers(server: ThreadingHTTPServer, state: RuntimeState) -> None:
    def handle_signal(signum: int, _frame: object) -> None:
        state.mark_draining()
        log_json("shutdown_requested", signal=signum)
        server.shutdown()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        log_json("config_error", error=str(exc))
        return 2

    state = RuntimeState.started_now()
    server = build_server(config, state)
    install_signal_handlers(server, state)
    log_json("service_started", service=config.app_name, port=config.port, environment=config.environment)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        log_json("service_stopped", service=config.app_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
