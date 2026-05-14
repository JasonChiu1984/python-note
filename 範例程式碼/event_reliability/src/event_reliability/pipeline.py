from __future__ import annotations

from collections import deque
from dataclasses import asdict
from typing import Callable

from .models import DomainEvent, EventEnvelope, OutboxEntry, ReliabilityReport


class FakeBroker:
    def __init__(self, publish_results: list[bool] | None = None) -> None:
        self.publish_results = deque(publish_results or [])
        self.published: list[EventEnvelope] = []

    def publish(self, envelope: EventEnvelope) -> None:
        result = self.publish_results.popleft() if self.publish_results else True
        if not result:
            raise RuntimeError("broker publish failed")
        self.published.append(envelope)


class IdempotentConsumer:
    def __init__(self, handler: Callable[[EventEnvelope], None]) -> None:
        self.handler = handler
        self.processed_event_ids: set[str] = set()
        self.handled: list[str] = []
        self.duplicate_skips = 0

    def consume(self, envelope: EventEnvelope) -> bool:
        if envelope.event_id in self.processed_event_ids:
            self.duplicate_skips += 1
            return False
        self.handler(envelope)
        self.processed_event_ids.add(envelope.event_id)
        self.handled.append(envelope.event_id)
        return True


class InMemoryEventStore:
    def __init__(self) -> None:
        self.pending: list[OutboxEntry] = []
        self.dlq: list[OutboxEntry] = []

    def record_change(self, event: DomainEvent) -> None:
        self.pending.append(OutboxEntry(event=event))


class EventPipeline:
    def __init__(
        self,
        broker: FakeBroker,
        consumer: IdempotentConsumer,
        *,
        max_delivery_attempts: int = 3,
        dispatch_batch_size: int = 50,
    ) -> None:
        self.store = InMemoryEventStore()
        self.broker = broker
        self.consumer = consumer
        self.max_delivery_attempts = max_delivery_attempts
        self.dispatch_batch_size = dispatch_batch_size
        self.report = ReliabilityReport()

    def enqueue_change(self, event: DomainEvent) -> None:
        self.store.record_change(event)

    def _to_envelope(self, event: DomainEvent) -> EventEnvelope:
        return EventEnvelope(
            event_id=event.event_id,
            stream_key=event.stream_key,
            event_type=event.event_type,
            version=event.version,
            payload=event.payload,
        )

    def dispatch_pending(self) -> None:
        remaining: list[OutboxEntry] = []
        for entry in self.store.pending[: self.dispatch_batch_size]:
            envelope = self._to_envelope(entry.event)
            try:
                self.broker.publish(envelope)
                self.report.dispatched += 1
                if self._consume_entry(entry, envelope):
                    remaining.append(entry)
            except RuntimeError as exc:
                entry.delivery_attempts += 1
                entry.last_error = str(exc)
                self.report.publish_failures += 1
                if entry.delivery_attempts >= self.max_delivery_attempts:
                    self.store.dlq.append(entry)
                    self.report.dlq_count = len(self.store.dlq)
                else:
                    remaining.append(entry)
        remaining.extend(self.store.pending[self.dispatch_batch_size :])
        self.store.pending = remaining
        self.report.processed_event_ids = sorted(self.consumer.processed_event_ids)

    def _consume_entry(self, entry: OutboxEntry, envelope: EventEnvelope) -> bool:
        try:
            consumed = self.consumer.consume(envelope)
        except RuntimeError as exc:
            entry.delivery_attempts += 1
            entry.last_error = str(exc)
            if entry.delivery_attempts >= self.max_delivery_attempts:
                self.store.dlq.append(entry)
                self.report.dlq_count = len(self.store.dlq)
            else:
                return True
            return False
        if consumed:
            self.report.processed += 1
        else:
            self.report.duplicate_skips = self.consumer.duplicate_skips
        return False

    def replay_dlq(self, index: int, replay_reason: str) -> None:
        entry = self.store.dlq.pop(index)
        entry.replay_count += 1
        entry.last_error = None
        entry.delivery_attempts = 0
        envelope = self._to_envelope(entry.event)
        try:
            self.consumer.consume(envelope)
        except RuntimeError as exc:
            entry.last_error = str(exc)
            self.store.dlq.append(entry)
            self.report.replay_failures += 1
            self.report.dlq_count = len(self.store.dlq)
            self.report.last_replay_reason = replay_reason
            return
        self.report.replayed += 1
        self.report.processed += 1
        self.report.dlq_count = len(self.store.dlq)
        self.report.last_replay_reason = replay_reason
        self.report.processed_event_ids = sorted(self.consumer.processed_event_ids)

    def snapshot_report(self) -> dict[str, object]:
        data = asdict(self.report)
        data["pending_count"] = len(self.store.pending)
        data["dlq_count"] = len(self.store.dlq)
        data["handled_order"] = list(self.consumer.handled)
        return data
