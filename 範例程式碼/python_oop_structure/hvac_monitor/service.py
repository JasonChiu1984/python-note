from collections import deque
from typing import Protocol

from .model import Reading


class ReadingSource(Protocol):
    def read(self) -> Reading: ...


def is_high(reading: Reading, limit_c: float) -> bool:
    return reading.celsius >= limit_c


class Monitor:
    def __init__(self, source: ReadingSource, history_size: int = 3) -> None:
        if history_size < 1:
            raise ValueError("history_size must be positive")
        self._source = source
        self._latest: dict[str, Reading] = {}
        self._recent: deque[Reading] = deque(maxlen=history_size)

    def poll(self) -> Reading:
        reading = self._source.read()
        self._latest[reading.sensor_id] = reading
        self._recent.append(reading)
        return reading

    def latest(self, sensor_id: str) -> Reading | None:
        return self._latest.get(sensor_id)

    def recent(self) -> tuple[Reading, ...]:
        return tuple(self._recent)
