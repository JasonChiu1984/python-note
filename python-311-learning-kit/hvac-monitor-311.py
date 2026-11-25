"""Offline Python 3.11 HVAC quality demo. No devices are contacted."""
import argparse
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import chain
import json
import math
from pathlib import Path
from types import MappingProxyType

MISSING = object()
LIMITS = MappingProxyType({"min_c": 18.0, "max_c": 30.0, "timeout_s": 0.05})
INPUTS = [
    [{"name": "T10", "value": 24.5}, {"name": "T11", "value": 31.2},
     {"name": "T12"}, {"name": "T13", "value": None}],
    [{"name": "T14", "value": "NaN"}, {"name": "T15", "value": True},
     {"name": "T16", "value": 17.0}, {"name": "T17", "delay": 1.0}],
]
EXPECTED = ["normal", "high", "no_field", "explicit_null", "non_finite",
            "invalid_type", "low", "read_timeout"]


@dataclass(frozen=True, slots=True)
class Point:
    name: str
    value: float | None
    quality: str
    state: str


async def collect_one(row: dict) -> Point:
    name = row["name"]
    try:
        async with asyncio.timeout(LIMITS["timeout_s"]):
            await asyncio.sleep(row.get("delay", 0))
    except TimeoutError:
        return Point(name, None, "timeout", "read_timeout")
    raw = row.get("value", MISSING)
    if raw is MISSING:
        return Point(name, None, "missing", "no_field")
    if raw is None:
        return Point(name, None, "missing", "explicit_null")
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return Point(name, None, "invalid", "invalid_type")
    try:
        value = float(raw)
    except (ValueError, OverflowError):
        return Point(name, None, "invalid", "invalid_number")
    if not math.isfinite(value):
        return Point(name, None, "invalid", "non_finite")
    state = "low" if value < LIMITS["min_c"] else "high" if value > LIMITS["max_c"] else "normal"
    return Point(name, value, "good", state)


async def collect() -> list[Point]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(collect_one(row)) for row in chain.from_iterable(INPUTS)]
    return [task.result() for task in tasks]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = asyncio.run(collect())
    assert [point.state for point in results] == EXPECTED
    assert [point.name for point in results] == [f"T{i}" for i in range(10, 18)]
    assert all(point.value is None for point in results if point.quality != "good")
    report = json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "points": [asdict(point) for point in results],
    }, ensure_ascii=False, allow_nan=False, indent=2)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
