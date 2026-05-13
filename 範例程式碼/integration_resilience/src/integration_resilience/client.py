from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import (
    CircuitOpenError,
    HttpTransport,
    IntegrationRequest,
    IntegrationResponse,
    RateLimitExceededError,
    ResponseValidationError,
    RetryNotAllowedError,
)
from .policies import CircuitBreaker, FixedWindowRateLimiter, IntegrationMetrics, RetryPolicy, validate_response


def no_sleep(seconds: float) -> None:
    """Default sleep hook for examples; tests keep it as a no-op."""


@dataclass
class ResilientIntegrationClient:
    transport: HttpTransport
    retry_policy: RetryPolicy
    circuit_breaker: CircuitBreaker
    rate_limiter: FixedWindowRateLimiter
    timeout_seconds: float = 2.0
    metrics: IntegrationMetrics | None = None
    sleep: Callable[[float], None] = no_sleep

    def __post_init__(self) -> None:
        if self.metrics is None:
            self.metrics = IntegrationMetrics()

    def call(self, request: IntegrationRequest, now_epoch: int) -> IntegrationResponse:
        assert self.metrics is not None
        try:
            self.rate_limiter.allow(now_epoch)
            self.circuit_breaker.before_call()
        except (CircuitOpenError, RateLimitExceededError) as exc:
            self.metrics.blocked += 1
            self.metrics.events.append(type(exc).__name__)
            raise

        last_response: IntegrationResponse | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            self.metrics.attempts += 1
            response = self.transport.send(request, timeout_seconds=self.timeout_seconds)
            last_response = IntegrationResponse(status_code=response.status_code, data=response.data, attempt_count=attempt)
            if last_response.ok:
                try:
                    validate_response(last_response)
                except ResponseValidationError:
                    self.metrics.schema_errors += 1
                    self.circuit_breaker.record_failure()
                    self.metrics.events.append("schema_error")
                    raise
                self.metrics.successes += 1
                self.circuit_breaker.record_success()
                self.metrics.events.append("success")
                return last_response

            self.circuit_breaker.record_failure()
            self.metrics.failures += 1
            if not self.retry_policy.should_retry(last_response, attempt):
                self.metrics.events.append(f"failed_status_{last_response.status_code}")
                return last_response
            if not request.can_retry():
                self.metrics.events.append("retry_not_allowed")
                raise RetryNotAllowedError("request cannot be retried without idempotency")
            self.metrics.retries += 1
            self.metrics.events.append(f"retry_{attempt}")
            self.sleep(self.retry_policy.backoff_seconds * attempt)

        assert last_response is not None
        return last_response
