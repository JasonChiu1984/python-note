from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SensorReading:
    sensor_id: str
    group: str
    value: float
    quality: str


def build_dataset(size: int = 1200) -> list[SensorReading]:
    if size <= 0:
        raise ValueError("size must be positive")
    groups = ("ahu", "chiller", "pump", "power")
    data: list[SensorReading] = []
    for index in range(size):
        group = groups[index % len(groups)]
        quality = "good" if index % 17 else "stale"
        value = round(18.0 + (index % 31) * 0.37 + (index % 5) * 0.11, 3)
        data.append(SensorReading(sensor_id=f"{group}-{index:05d}", group=group, value=value, quality=quality))
    return data


def slow_group_totals(readings: list[SensorReading]) -> dict[str, float]:
    groups = sorted({reading.group for reading in readings})
    totals: dict[str, float] = {}
    for group in groups:
        group_total = 0.0
        for reading in readings:
            if reading.group == group and reading.quality == "good":
                group_total += reading.value
        totals[group] = round(group_total, 3)
    return totals


def optimized_group_totals(readings: list[SensorReading]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for reading in readings:
        if reading.quality != "good":
            continue
        totals[reading.group] = totals.get(reading.group, 0.0) + reading.value
    return {group: round(total, 3) for group, total in sorted(totals.items())}
