from __future__ import annotations

import json

from .service import ObservedService
from .telemetry import TelemetryCollector


def main() -> int:
    collector = TelemetryCollector()
    service = ObservedService(collector)
    service.handle_request("/orders", trace_id="demo-trace-1", dependency_latency_ms=42)
    service.handle_request("/orders", trace_id="demo-trace-2", dependency_latency_ms=135)
    health = service.health_report(dependency_latency_ms=135, dependency_ok=True)
    result = {
        "logs": collector.logs,
        "spans": collector.spans,
        "metrics": collector.metrics_snapshot(),
        "health": health,
        "slo": collector.evaluate_slo(max_error_rate=0.6, max_average_latency_ms=200),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
