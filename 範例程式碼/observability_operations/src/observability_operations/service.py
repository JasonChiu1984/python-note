from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .health import DependencyState, build_health_report
from .telemetry import TelemetryCollector, new_trace_id


@dataclass
class ObservedService:
    telemetry: TelemetryCollector
    version: str = "v2.1.0"

    def handle_request(
        self,
        route: str,
        *,
        trace_id: str | None = None,
        dependency_latency_ms: float = 35.0,
        fail_dependency: bool = False,
    ) -> dict[str, Any]:
        trace_id = trace_id or new_trace_id()
        started = perf_counter()
        span = self.telemetry.start_span("service.handle_request", trace_id)
        self.telemetry.log("info", "request.started", trace_id, route=route, version=self.version)

        dependency_timeout = dependency_latency_ms > 100.0 or fail_dependency
        status = "ok"
        error_type = None
        response: dict[str, Any] = {"ok": True, "route": route, "trace_id": trace_id}

        if dependency_timeout:
            status = "error"
            error_type = "DependencyTimeout"
            response = {"ok": False, "route": route, "trace_id": trace_id, "error": error_type}
            self.telemetry.log(
                "error",
                "dependency.timeout",
                trace_id,
                route=route,
                dependency="orders-db",
                duration_ms=dependency_latency_ms,
                token="should-not-leak",
            )

        duration_ms = (perf_counter() - started) * 1000 + dependency_latency_ms
        self.telemetry.finish_span(span, status=status, error_type=error_type)
        self.telemetry.record_request(duration_ms, ok=not dependency_timeout, dependency_timeout=dependency_timeout)
        self.telemetry.log(
            "info",
            "request.completed",
            trace_id,
            route=route,
            duration_ms=round(duration_ms, 3),
            ok=not dependency_timeout,
        )
        return response

    def health_report(self, dependency_latency_ms: float = 35.0, dependency_ok: bool = True) -> dict[str, object]:
        dependency = DependencyState(name="orders-db", ok=dependency_ok, latency_ms=dependency_latency_ms)
        return build_health_report([dependency])
