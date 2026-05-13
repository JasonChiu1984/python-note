from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, TypedDict


class IntegrationError(RuntimeError):
    """Base error for integration policy failures."""


class RetryNotAllowedError(IntegrationError):
    """Raised when a non-idempotent request would otherwise be retried."""


class CircuitOpenError(IntegrationError):
    """Raised when circuit breaker blocks an external dependency."""


class RateLimitExceededError(IntegrationError):
    """Raised when the local caller exceeds the configured call budget."""


class ResponseValidationError(IntegrationError):
    """Raised when the external service response does not match the contract."""


class Method(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class ResponsePayload(TypedDict):
    status: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class IntegrationRequest:
    method: Method
    path: str
    body: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None

    def can_retry(self) -> bool:
        if self.method in {Method.GET, Method.PUT, Method.DELETE}:
            return True
        return bool(self.idempotency_key)


@dataclass(frozen=True)
class IntegrationResponse:
    status_code: int
    data: ResponsePayload
    attempt_count: int

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class HttpTransport(Protocol):
    def send(self, request: IntegrationRequest, timeout_seconds: float) -> IntegrationResponse:
        """Send a request to an external API, device gateway, or service."""
