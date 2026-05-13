from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class ReadingStatus(str, Enum):
    OK = "ok"
    STALE = "stale"
    FAULT = "fault"


class ReadingPayload(TypedDict):
    schema_version: str
    device_id: str
    point: str
    value: float
    unit: str
    timestamp: int
    status: str


@dataclass(frozen=True)
class SensorReading:
    schema_version: str
    device_id: str
    point: str
    value: float
    unit: str
    timestamp: int
    status: ReadingStatus

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported schema_version")
        if not self.device_id.strip():
            raise ValueError("device_id is required")
        if not self.point.strip():
            raise ValueError("point is required")
        if self.unit != "C":
            raise ValueError("only Celsius readings are supported in this sample")
        if not 0 <= self.value <= 100:
            raise ValueError("temperature reading is outside the safety envelope")
        if self.timestamp <= 0:
            raise ValueError("timestamp must be positive")


@dataclass(frozen=True)
class AlarmEvent:
    device_id: str
    point: str
    severity: str
    message: str
    fail_safe_required: bool
