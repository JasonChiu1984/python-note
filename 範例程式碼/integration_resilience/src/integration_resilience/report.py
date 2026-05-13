from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .policies import IntegrationMetrics


@dataclass(frozen=True)
class IntegrationReport:
    policy_version: str
    timeout_seconds: float
    max_attempts: int
    idempotency_checked: bool
    circuit_breaker_checked: bool
    schema_validation_checked: bool
    metrics: IntegrationMetrics

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "timeout_seconds": self.timeout_seconds,
            "max_attempts": self.max_attempts,
            "idempotency_checked": self.idempotency_checked,
            "circuit_breaker_checked": self.circuit_breaker_checked,
            "schema_validation_checked": self.schema_validation_checked,
            "metrics": {
                "attempts": self.metrics.attempts,
                "retries": self.metrics.retries,
                "successes": self.metrics.successes,
                "failures": self.metrics.failures,
                "blocked": self.metrics.blocked,
                "schema_errors": self.metrics.schema_errors,
                "events": list(self.metrics.events),
            },
        }


def write_integration_report(path: Path, report: IntegrationReport) -> None:
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
