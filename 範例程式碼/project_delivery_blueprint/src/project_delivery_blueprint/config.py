from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ServiceConfig:
    site_name: str
    poll_interval_seconds: int = 15
    temperature_alarm_c: float = 45.0
    max_batch_size: int = 50

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "ServiceConfig":
        site_name = values.get("site_name", "").strip()
        if not site_name:
            raise ValueError("site_name is required")

        poll_interval = int(values.get("poll_interval_seconds", "15"))
        if poll_interval < 1:
            raise ValueError("poll_interval_seconds must be >= 1")

        alarm_c = float(values.get("temperature_alarm_c", "45.0"))
        max_batch_size = int(values.get("max_batch_size", "50"))
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be >= 1")

        return cls(
            site_name=site_name,
            poll_interval_seconds=poll_interval,
            temperature_alarm_c=alarm_c,
            max_batch_size=max_batch_size,
        )
