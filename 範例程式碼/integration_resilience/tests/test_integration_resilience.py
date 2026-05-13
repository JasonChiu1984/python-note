from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from integration_resilience.client import ResilientIntegrationClient
from integration_resilience.models import (
    CircuitOpenError,
    IntegrationRequest,
    IntegrationResponse,
    Method,
    RateLimitExceededError,
    ResponseValidationError,
    RetryNotAllowedError,
)
from integration_resilience.policies import CircuitBreaker, FixedWindowRateLimiter, RetryPolicy
from integration_resilience.report import IntegrationReport, write_integration_report
from integration_resilience.testing import FakeTransport


def make_client(responses: list[IntegrationResponse], max_attempts: int = 3) -> ResilientIntegrationClient:
    return ResilientIntegrationClient(
        transport=FakeTransport(responses=responses),
        retry_policy=RetryPolicy(max_attempts=max_attempts),
        circuit_breaker=CircuitBreaker(failure_threshold=5),
        rate_limiter=FixedWindowRateLimiter(limit=10),
    )


class IntegrationResilienceTests(unittest.TestCase):
    def test_retry_succeeds_for_idempotent_post(self) -> None:
        client = make_client(
            [
                IntegrationResponse(status_code=503, data={"status": "degraded", "payload": {}}, attempt_count=1),
                IntegrationResponse(status_code=200, data={"status": "ok", "payload": {"value": 1}}, attempt_count=2),
            ]
        )
        request = IntegrationRequest(method=Method.POST, path="/api/write", idempotency_key="write-1")
        response = client.call(request, now_epoch=1778677200)
        self.assertTrue(response.ok)
        self.assertEqual(response.attempt_count, 2)
        self.assertEqual(client.metrics.retries, 1)

    def test_post_without_idempotency_is_not_retried(self) -> None:
        client = make_client(
            [IntegrationResponse(status_code=503, data={"status": "degraded", "payload": {}}, attempt_count=1)]
        )
        request = IntegrationRequest(method=Method.POST, path="/api/write")
        with self.assertRaises(RetryNotAllowedError):
            client.call(request, now_epoch=1778677200)

    def test_circuit_breaker_blocks_after_threshold(self) -> None:
        transport = FakeTransport(
            responses=[
                IntegrationResponse(status_code=503, data={"status": "degraded", "payload": {}}, attempt_count=1),
                IntegrationResponse(status_code=503, data={"status": "degraded", "payload": {}}, attempt_count=2),
            ]
        )
        client = ResilientIntegrationClient(
            transport=transport,
            retry_policy=RetryPolicy(max_attempts=1),
            circuit_breaker=CircuitBreaker(failure_threshold=2),
            rate_limiter=FixedWindowRateLimiter(limit=10),
        )
        request = IntegrationRequest(method=Method.GET, path="/api/status")
        client.call(request, now_epoch=1778677200)
        client.call(request, now_epoch=1778677201)
        with self.assertRaises(CircuitOpenError):
            client.call(request, now_epoch=1778677202)

    def test_rate_limiter_blocks_excess_calls(self) -> None:
        client = ResilientIntegrationClient(
            transport=FakeTransport(
                responses=[
                    IntegrationResponse(status_code=200, data={"status": "ok", "payload": {}}, attempt_count=1),
                    IntegrationResponse(status_code=200, data={"status": "ok", "payload": {}}, attempt_count=1),
                ]
            ),
            retry_policy=RetryPolicy(max_attempts=1),
            circuit_breaker=CircuitBreaker(failure_threshold=5),
            rate_limiter=FixedWindowRateLimiter(limit=1),
        )
        request = IntegrationRequest(method=Method.GET, path="/api/status")
        client.call(request, now_epoch=1778677200)
        with self.assertRaises(RateLimitExceededError):
            client.call(request, now_epoch=1778677201)

    def test_response_schema_validation_blocks_bad_payload(self) -> None:
        client = make_client([IntegrationResponse(status_code=200, data={"status": "ok"}, attempt_count=1)], max_attempts=1)
        with self.assertRaises(ResponseValidationError):
            client.call(IntegrationRequest(method=Method.GET, path="/api/status"), now_epoch=1778677200)
        self.assertEqual(client.metrics.schema_errors, 1)

    def test_integration_report_is_written_as_json(self) -> None:
        metrics = make_client(
            [IntegrationResponse(status_code=200, data={"status": "ok", "payload": {}}, attempt_count=1)],
            max_attempts=1,
        ).metrics
        report = IntegrationReport(
            policy_version="1.0",
            timeout_seconds=2.0,
            max_attempts=3,
            idempotency_checked=True,
            circuit_breaker_checked=True,
            schema_validation_checked=True,
            metrics=metrics,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "integration_resilience_report.json"
            write_integration_report(path, report)
            text = path.read_text(encoding="utf-8")
        self.assertIn('"policy_version": "1.0"', text)
        self.assertIn('"schema_validation_checked": true', text)


if __name__ == "__main__":
    unittest.main()
