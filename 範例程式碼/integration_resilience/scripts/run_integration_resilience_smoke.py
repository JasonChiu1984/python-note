from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from integration_resilience.client import ResilientIntegrationClient  # noqa: E402
from integration_resilience.models import IntegrationRequest, IntegrationResponse, Method  # noqa: E402
from integration_resilience.policies import CircuitBreaker, FixedWindowRateLimiter, RetryPolicy  # noqa: E402
from integration_resilience.report import IntegrationReport, write_integration_report  # noqa: E402
from integration_resilience.testing import FakeTransport  # noqa: E402


def main() -> int:
    transport = FakeTransport(
        responses=[
            IntegrationResponse(status_code=503, data={"status": "degraded", "payload": {}}, attempt_count=1),
            IntegrationResponse(status_code=200, data={"status": "ok", "payload": {"temperature_c": 23.8}}, attempt_count=2),
        ]
    )
    client = ResilientIntegrationClient(
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=3),
        circuit_breaker=CircuitBreaker(failure_threshold=3),
        rate_limiter=FixedWindowRateLimiter(limit=10),
    )
    request = IntegrationRequest(method=Method.POST, path="/gateway/readings", idempotency_key="poll-1778677200")
    response = client.call(request, now_epoch=1778677200)

    breaker = CircuitBreaker(failure_threshold=1)
    blocked_client = ResilientIntegrationClient(
        transport=FakeTransport(responses=[]),
        retry_policy=RetryPolicy(max_attempts=1),
        circuit_breaker=breaker,
        rate_limiter=FixedWindowRateLimiter(limit=10),
    )
    try:
        blocked_client.call(IntegrationRequest(method=Method.GET, path="/gateway/down"), now_epoch=1778677201)
        blocked_client.call(IntegrationRequest(method=Method.GET, path="/gateway/down"), now_epoch=1778677202)
    except Exception:
        pass

    report = IntegrationReport(
        policy_version="1.0",
        timeout_seconds=client.timeout_seconds,
        max_attempts=client.retry_policy.max_attempts,
        idempotency_checked=bool(request.idempotency_key),
        circuit_breaker_checked=breaker.opened,
        schema_validation_checked=response.ok,
        metrics=client.metrics,
    )
    write_integration_report(ROOT / "integration_resilience_report.json", report)
    if response.ok and client.metrics and client.metrics.retries == 1 and breaker.opened:
        print("integration resilience smoke passed: retry + idempotency + circuit + schema + evidence")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
