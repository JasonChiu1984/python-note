from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import AlarmEvent, ReadingStatus, SensorReading


class AlarmPublisher(Protocol):
    def publish(self, event: AlarmEvent) -> None:
        """Publish an alarm event to an external channel."""


@dataclass
class InMemoryAlarmPublisher:
    events: list[AlarmEvent] = field(default_factory=list)

    def publish(self, event: AlarmEvent) -> None:
        self.events.append(event)


@dataclass
class GatewayService:
    publisher: AlarmPublisher
    alarm_threshold_c: float = 38.0
    stale_timeout_seconds: int = 30

    def evaluate(self, reading: SensorReading, now_epoch: int) -> AlarmEvent | None:
        stale = now_epoch - reading.timestamp > self.stale_timeout_seconds
        if reading.status in {ReadingStatus.STALE, ReadingStatus.FAULT} or stale:
            event = AlarmEvent(
                device_id=reading.device_id,
                point=reading.point,
                severity="critical",
                message="reading stale or device fault; fail-safe output required",
                fail_safe_required=True,
            )
            self.publisher.publish(event)
            return event
        if reading.value >= self.alarm_threshold_c:
            event = AlarmEvent(
                device_id=reading.device_id,
                point=reading.point,
                severity="warning",
                message=f"temperature {reading.value:.1f}C reached alarm threshold",
                fail_safe_required=False,
            )
            self.publisher.publish(event)
            return event
        return None
