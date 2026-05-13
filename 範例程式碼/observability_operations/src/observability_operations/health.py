from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyState:
    name: str
    ok: bool
    latency_ms: float
    timeout_ms: float = 100.0

    @property
    def timed_out(self) -> bool:
        return self.latency_ms > self.timeout_ms


def build_health_report(dependencies: list[DependencyState]) -> dict[str, object]:
    failed = [item for item in dependencies if not item.ok or item.timed_out]
    degraded = [item for item in dependencies if item.ok and item.latency_ms > item.timeout_ms * 0.75]
    return {
        "live": "ok",
        "ready": "fail" if failed else "ok",
        "status": "degraded" if failed or degraded else "ok",
        "dependencies": [
            {
                "name": item.name,
                "ok": item.ok,
                "latency_ms": item.latency_ms,
                "timed_out": item.timed_out,
            }
            for item in dependencies
        ],
    }
