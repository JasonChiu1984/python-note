from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    stream_key: str
    event_type: str
    version: int
    payload: dict[str, Any]
    occurred_at: str


@dataclass
class OutboxEntry:
    event: DomainEvent
    delivery_attempts: int = 0
    last_error: str | None = None
    replay_count: int = 0


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    stream_key: str
    event_type: str
    version: int
    payload: dict[str, Any]


@dataclass
class ReliabilityReport:
    dispatched: int = 0
    publish_failures: int = 0
    processed: int = 0
    duplicate_skips: int = 0
    dlq_count: int = 0
    replayed: int = 0
    replay_failures: int = 0
    last_replay_reason: str | None = None
    processed_event_ids: list[str] = field(default_factory=list)
