from __future__ import annotations

from .models import DomainEvent


def make_event(event_id: str, *, payload: dict[str, object] | None = None, stream_key: str = "order-1001") -> DomainEvent:
    return DomainEvent(
        event_id=event_id,
        stream_key=stream_key,
        event_type="OrderCreated",
        version=1,
        payload=payload or {"order_id": stream_key, "status": "created"},
        occurred_at="2026-05-14T15:07:40+08:00",
    )
