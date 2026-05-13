"""Health and readiness contracts for the sample service."""

from __future__ import annotations

from dataclasses import dataclass
import time

from .config import RuntimeConfig


@dataclass
class RuntimeState:
    started_at: float
    draining: bool = False

    @classmethod
    def started_now(cls) -> "RuntimeState":
        return cls(started_at=time.time())

    def mark_draining(self) -> None:
        self.draining = True


def health_report(config: RuntimeConfig, state: RuntimeState) -> tuple[int, dict[str, object]]:
    status = "draining" if state.draining else "ok"
    return 200, {
        "status": status,
        "service": config.app_name,
        "environment": config.environment,
        "uptime_seconds": max(0, round(time.time() - state.started_at, 3)),
    }


def readiness_report(config: RuntimeConfig, state: RuntimeState) -> tuple[int, dict[str, object]]:
    if state.draining:
        return 503, {
            "status": "not_ready",
            "reason": "service is draining",
            "dependency_status": config.dependency_status,
        }
    if config.dependency_status != "healthy":
        return 503, {
            "status": "not_ready",
            "reason": "dependency is not healthy",
            "dependency_status": config.dependency_status,
        }
    return 200, {
        "status": "ready",
        "dependency_status": config.dependency_status,
    }
