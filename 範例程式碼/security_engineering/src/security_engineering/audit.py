from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SENSITIVE_KEYS = {"password", "token", "secret", "authorization"}


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: ("***" if key.lower() in SENSITIVE_KEYS else value) for key, value in fields.items()}


@dataclass
class AuditLog:
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(self, event: str, actor: str, trace_id: str, **fields: Any) -> dict[str, Any]:
        item = {"event": event, "actor": actor, "trace_id": trace_id, **redact(fields)}
        self.events.append(item)
        return item
