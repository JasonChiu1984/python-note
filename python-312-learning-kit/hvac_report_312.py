"""Simulated 8-point collector and JSON report. No external equipment or network."""
import argparse
import asyncio
import json
import math
from pathlib import Path

POINTS = [
    ("AHU-01", 24.6, 0.001), ("AHU-02", 28.1, 0.002),
    ("AHU-03", 25.2, 0.001), ("AHU-04", None, 0.001),
    ("AHU-05", 26.8, 0.002), ("AHU-06", 29.5, 0.001),
    ("AHU-07", 27.4, 0.050), ("AHU-08", 25.7, 0.001),
]


def normalize(row):
    if "celsius" not in row:
        return "missing", None
    value = row["celsius"]
    if type(value) not in (int, float) or not -40 <= value <= 90 or not math.isfinite(value):
        return "invalid", None
    return "valid", value


async def sample(point, value, delay):
    try:
        async with asyncio.timeout(0.020):
            await asyncio.sleep(delay)
    except TimeoutError:
        return {"point": point, "quality": "timeout", "celsius": None}
    quality, reading = normalize({"celsius": value})
    return {"point": point, "quality": quality, "celsius": reading}


async def collect():
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(sample(*row)) for row in POINTS]
    rows = [task.result() for task in tasks]
    values = [r["celsius"] for r in rows if r["quality"] == "valid"]
    return {
        "rows": rows,
        "valid_count": len(values),
        "alarms": [r["point"] for r in rows if r["quality"] == "valid" and r["celsius"] >= 28],
        "mean_celsius": round(sum(values) / len(values), 3) if values else None,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, help="Create a new report path without overwriting it")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    report = asyncio.run(collect())
    if args.self_test:
        assert len(report["rows"]) == 8 and report["valid_count"] == 6
        assert report["alarms"] == ["AHU-02", "AHU-06"]
        assert report["rows"][3]["quality"] == "invalid"
        assert report["rows"][6]["quality"] == "timeout"
        assert report["mean_celsius"] == 26.65
        assert normalize({}) == ("missing", None)
        for bad in (None, float("nan"), float("inf"), True, -41, 91, "28"):
            assert normalize({"celsius": bad}) == ("invalid", None)
        assert normalize({"celsius": 0}) == ("valid", 0)
    body = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output is None:
        print(body, end="")
    else:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(body)


if __name__ == "__main__":
    main()
