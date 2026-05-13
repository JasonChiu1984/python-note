from __future__ import annotations

from dataclasses import dataclass, field

from .models import CircuitOpenError, IntegrationResponse, RateLimitExceededError, ResponseValidationError


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.2
    retry_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504)

    def should_retry(self, response: IntegrationResponse, attempt: int) -> bool:
        return attempt < self.max_attempts and response.status_code in self.retry_statuses


@dataclass
class CircuitBreaker:
    failure_threshold: int = 2
    failure_count: int = 0
    opened: bool = False

    def before_call(self) -> None:
        if self.opened:
            raise CircuitOpenError("external dependency circuit is open")

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened = False

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened = True


@dataclass
class FixedWindowRateLimiter:
    limit: int
    window_seconds: int = 60
    _window_start: int | None = None
    _count: int = 0

    def allow(self, now_epoch: int) -> None:
        if self._window_start is None or now_epoch - self._window_start >= self.window_seconds:
            self._window_start = now_epoch
            self._count = 0
        if self._count >= self.limit:
            raise RateLimitExceededError("external dependency rate limit exceeded")
        self._count += 1


@dataclass
class IntegrationMetrics:
    attempts: int = 0
    retries: int = 0
    successes: int = 0
    failures: int = 0
    blocked: int = 0
    schema_errors: int = 0
    events: list[str] = field(default_factory=list)


def validate_response(response: IntegrationResponse) -> None:
    data = response.data
    if not isinstance(data, dict):
        raise ResponseValidationError("response data must be a dict")
    if data.get("status") not in {"ok", "accepted", "degraded"}:
        raise ResponseValidationError("response status must be ok, accepted, or degraded")
    if not isinstance(data.get("payload"), dict):
        raise ResponseValidationError("response payload must be a dict")
