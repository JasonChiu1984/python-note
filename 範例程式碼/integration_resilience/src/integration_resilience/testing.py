from __future__ import annotations

from dataclasses import dataclass, field

from .models import IntegrationRequest, IntegrationResponse


@dataclass
class FakeTransport:
    responses: list[IntegrationResponse]
    calls: list[IntegrationRequest] = field(default_factory=list)

    def send(self, request: IntegrationRequest, timeout_seconds: float) -> IntegrationResponse:
        self.calls.append(request)
        if not self.responses:
            return IntegrationResponse(status_code=503, data={"status": "degraded", "payload": {}}, attempt_count=len(self.calls))
        response = self.responses.pop(0)
        return IntegrationResponse(status_code=response.status_code, data=response.data, attempt_count=len(self.calls))
