from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Snapshot:
    device_id: str
    message_id: str
    temperature_c: float
    status: str


@dataclass(frozen=True)
class CycleReport:
    site_name: str
    processed_count: int
    duplicate_count: int
    alarm_count: int
    fail_safe_devices: tuple[str, ...] = field(default_factory=tuple)
