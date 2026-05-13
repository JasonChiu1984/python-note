from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from time import perf_counter
from typing import Any
from uuid import uuid4


def new_trace_id() -> str:
    return uuid4().hex


@dataclass
class Span:
    name: str
    trace_id: str
    start_ms: float = field(default_factory=lambda: perf_counter() * 1000)
    end_ms: float | None = None
    status: str = "ok"
    error_type: str | None = None

    def finish(self, status: str = "ok", error_type: str | None = None) -> dict[str, Any]:
        self.end_ms = perf_counter() * 1000
        self.status = status
        self.error_type = error_type
        return {
            "event": "span.finished",
            "trace_id": self.trace_id,
            "span": self.name,
            "status": self.status,
            "duration_ms": round(self.end_ms - self.start_ms, 3),
            "error_type": self.error_type,
        }


@dataclass
class TelemetryCollector:
    logs: list[dict[str, Any]] = field(default_factory=list)
    spans: list[dict[str, Any]] = field(default_factory=list)
    request_latencies_ms: list[float] = field(default_factory=list)
    requests_total: int = 0
    errors_total: int = 0
    dependency_timeouts_total: int = 0

    def log(self, level: str, event: str, trace_id: str, **fields: Any) -> dict[str, Any]:
        record = {"level": level, "event": event, "trace_id": trace_id, **self._redact(fields)}
        self.logs.append(record)
        return record

    def start_span(self, name: str, trace_id: str) -> Span:
        return Span(name=name, trace_id=trace_id)

    def finish_span(self, span: Span, status: str = "ok", error_type: str | None = None) -> dict[str, Any]:
        event = span.finish(status=status, error_type=error_type)
        self.spans.append(event)
        return event

    def record_request(self, duration_ms: float, ok: bool, dependency_timeout: bool = False) -> None:
        self.requests_total += 1
        self.request_latencies_ms.append(duration_ms)
        if not ok:
            self.errors_total += 1
        if dependency_timeout:
            self.dependency_timeouts_total += 1

    def metrics_snapshot(self) -> dict[str, float | int]:
        average_latency = mean(self.request_latencies_ms) if self.request_latencies_ms else 0.0
        error_rate = self.errors_total / self.requests_total if self.requests_total else 0.0
        return {
            "requests_total": self.requests_total,
            "errors_total": self.errors_total,
            "dependency_timeouts_total": self.dependency_timeouts_total,
            "average_latency_ms": round(average_latency, 3),
            "error_rate": round(error_rate, 4),
        }

    def evaluate_slo(self, max_error_rate: float = 0.05, max_average_latency_ms: float = 250.0) -> dict[str, Any]:
        metrics = self.metrics_snapshot()
        passed = metrics["error_rate"] <= max_error_rate and metrics["average_latency_ms"] <= max_average_latency_ms
        return {
            "slo": "request-quality",
            "passed": bool(passed),
            "max_error_rate": max_error_rate,
            "max_average_latency_ms": max_average_latency_ms,
            "metrics": metrics,
        }

    def _redact(self, fields: dict[str, Any]) -> dict[str, Any]:
        redacted = dict(fields)
        for key in ("token", "password", "secret"):
            if key in redacted:
                redacted[key] = "***"
        return redacted
