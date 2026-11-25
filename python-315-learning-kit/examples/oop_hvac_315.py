"""Replay a software-only HVAC monitoring scenario from the OOP chapter."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import isfinite
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Reading:
    point: str
    celsius: float

    def __post_init__(self) -> None:
        if not self.point.strip():
            raise ValueError("point must not be blank")
        if not isfinite(self.celsius):
            raise ValueError("celsius must be finite")


class ReadingSource(Protocol):
    def read(self) -> Reading: ...


class ReplaySource:
    def __init__(self, readings: Iterable[Reading]) -> None:
        self._readings = iter(readings)

    def read(self) -> Reading:
        return next(self._readings)


class OffsetSource:
    def __init__(self, source: ReadingSource, offset_c: float) -> None:
        if not isfinite(offset_c):
            raise ValueError("offset_c must be finite")
        self._source = source
        self._offset_c = offset_c

    def read(self) -> Reading:
        reading = self._source.read()
        return replace(reading, celsius=reading.celsius + self._offset_c)


@dataclass(frozen=True, slots=True)
class Assessment:
    reading: Reading
    over_limit: bool


class Monitor:
    def __init__(self, source: ReadingSource, limit_c: float) -> None:
        if not isfinite(limit_c):
            raise ValueError("limit_c must be finite")
        self._source = source
        self._limit_c = limit_c

    def scan(self) -> Assessment:
        reading = self._source.read()
        return Assessment(reading, reading.celsius >= self._limit_c)


def main() -> None:
    samples = [
        Reading("AHU-01", 23.0),
        Reading("AHU-01", 24.5),
        Reading("AHU-02", 25.0),
    ]
    source = OffsetSource(ReplaySource(samples), offset_c=0.5)
    monitor = Monitor(source, limit_c=25.0)

    for _ in samples:
        result = monitor.scan()
        status = "HIGH" if result.over_limit else "OK"
        reading = result.reading
        print(f"{reading.point} {reading.celsius:.1f} C {status}")


if __name__ == "__main__":
    main()
