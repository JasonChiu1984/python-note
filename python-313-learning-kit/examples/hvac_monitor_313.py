"""Python 3.13 語法整合練習：模擬測點驗證與告警報告。

只讀取此檔內建的模擬資料，不連線或控制任何設備。
執行：python3.13 hvac_monitor_313.py --output report.json
"""

import argparse
import asyncio
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Literal


MISSING = object()  # 本行程內的缺欄位標記，以 is 比對
DEFAULTS = MappingProxyType({"low_c": 18.0, "high_c": 28.0, "timeout_s": 0.05})
type Quality = Literal["good", "missing", "invalid", "timeout"]


@dataclass(frozen=True, slots=True)
class Reading:
    sensor: str
    value_c: float | None
    quality: Quality
    status: str


def validate(sensor: str, raw: object) -> Reading:
    """把輸入品質和超限狀態分開，拒絕布林值、NaN 和無窮大。"""
    if raw is MISSING:
        return Reading(sensor, None, "missing", "no_field")
    if raw is None:
        return Reading(sensor, None, "missing", "explicit_null")
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return Reading(sensor, None, "invalid", "invalid_type")
    try:
        value = float(raw)
    except (ValueError, OverflowError):
        return Reading(sensor, None, "invalid", "invalid_number")
    if not math.isfinite(value):
        return Reading(sensor, None, "invalid", "non_finite")
    if value > DEFAULTS["high_c"]:
        status = "high"
    elif value < DEFAULTS["low_c"]:
        status = "low"
    else:
        status = "normal"
    return Reading(sensor, value, "good", status)


async def simulated_read(raw: object, delay: float) -> object:
    await asyncio.sleep(delay)
    return raw


async def collect_one(sensor: str, raw: object, delay: float) -> Reading:
    try:
        async with asyncio.timeout(DEFAULTS["timeout_s"]):
            value = await simulated_read(raw, delay)
    except TimeoutError:
        return Reading(sensor, None, "timeout", "read_timeout")
    return validate(sensor, value)


async def collect_all() -> list[Reading]:
    batches = [
        [("T10", 24.5, 0.001), ("T11", 31.2, 0.001)],
        [("T12", MISSING, 0.001), ("T13", None, 0.001)],
        [("T14", "NaN", 0.001), ("T15", True, 0.001)],
        [("T16", 17.0, 0.001), ("T17", 22.0, 0.15)],
    ]
    specs = [spec for batch in batches for spec in batch]
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(collect_one(*spec)) for spec in specs]
    return [task.result() for task in tasks]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="另存 UTF-8 JSON 報告")
    args = parser.parse_args()
    readings = asyncio.run(collect_all())
    report = {
        "simulated": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": dict(DEFAULTS),
        "quality_counts": dict(Counter(r.quality for r in readings)),
        "status_counts": dict(Counter(r.status for r in readings)),
        "readings": [asdict(r) for r in readings],
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output is not None:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
