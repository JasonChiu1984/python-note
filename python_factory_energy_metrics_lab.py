"""工廠電力與良品能效：同一條線、四個 15 分鐘合成區間。Python 3.10+。"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Iterable
import unittest

INTERVAL = timedelta(minutes=15)
HOURS = 0.25
TAIPEI = timezone(timedelta(hours=8))
FIELDS = ("start", "energy_kwh", "good_a", "good_b")


@dataclass(frozen=True)
class Window:
    start: datetime
    energy_kwh: float
    good_a: int
    good_b: int


def from_records(items: Iterable[dict]) -> list[Window]:
    """CSV DictReader 或 JSON 物件列 → 同一內部型別；不猜單位或時區。"""
    rows = []
    for item in items:
        ts = datetime.fromisoformat(str(item["start"]))
        if ts.utcoffset() is None:
            raise ValueError("start 必須含時區")
        energy = float(item["energy_kwh"])
        counts = []
        for name in ("good_a", "good_b"):
            raw = str(item[name]).strip()
            if not raw.isascii() or not raw.isdecimal():
                raise ValueError(f"{name} 必須是非負整數")
            counts.append(int(raw))
        rows.append(Window(ts, energy, *counts))
    return rows


def difference_kwh(previous: float, current: float) -> float:
    """同一電表正向累積表讀值；重設／回捲不能冒充有效用電。"""
    if not all(math.isfinite(x) and x >= 0 for x in (previous, current)):
        raise ValueError("電表讀值無效")
    if current < previous:
        raise ValueError("電表倒退：查換表、重設、回捲或方向配置")
    return current - previous


def summarize(rows: Iterable[Window], expected_start: datetime, periods: int) -> dict:
    if expected_start.utcoffset() is None or periods < 1:
        raise ValueError("必須指定含時區的首區間與預期筆數")
    t = expected_start.astimezone(timezone.utc)
    if t.minute % 15 or t.second or t.microsecond:
        raise ValueError("首區間須對齊固定 15 分鐘邊界")
    data = list(rows)
    if any(x.start.utcoffset() is None for x in data):
        raise ValueError("時間缺少時區")
    data.sort(key=lambda x: x.start.astimezone(timezone.utc))
    expected = [t + i * INTERVAL for i in range(periods)]
    if [x.start.astimezone(timezone.utc) for x in data] != expected:
        raise ValueError("缺值、重複或區間不對齊；勿填零後發布")
    if any(not math.isfinite(x.energy_kwh) or x.energy_kwh < 0 or
           type(x.good_a) is not int or type(x.good_b) is not int or
           x.good_a < 0 or x.good_b < 0 for x in data):
        raise ValueError("kWh 或良品數不合法")
    e = math.fsum(x.energy_kwh for x in data)
    a, b = sum(x.good_a for x in data), sum(x.good_b for x in data)
    peak = max(x.energy_kwh for x in data) / HOURS
    mean = e / (HOURS * periods)
    # 合成、事先固定的基準：每 15 分鐘固定負荷 25 kWh；
    # A 每件 0.25 kWh、B 每件 0.50 kWh。不是用本批報告資料回歸。
    baseline = 25 * periods + 0.25 * a + 0.50 * b
    return {
        "start": expected_start.isoformat(), "interval_minutes": 15, "periods": periods,
        "energy_kwh": e, "good_a": a, "good_b": b, "good_total": a + b,
        "sec_kwh_per_good": e / (a + b) if a + b else None,
        "peak_interval_kw": peak, "mean_kw": mean, "load_factor": mean / peak if peak else None,
        "baseline_kwh_same_mix": baseline, "difference_kwh": baseline - e,
        "difference_ratio": (baseline - e) / baseline,
        "demand_kw": [x.energy_kwh / HOURS for x in data],
    }


def demo() -> tuple[datetime, list[Window]]:
    start = datetime(2026, 11, 25, 8, tzinfo=TAIPEI)
    vals = [(51, 60, 20), (65, 40, 60), (55, 80, 20), (39, 0, 0)]
    return start, [Window(start + i * INTERVAL, *v) for i, v in enumerate(vals)]


class LabTests(unittest.TestCase):
    def test_nominal(self):
        start, data = demo()
        r = summarize(data, start, 4)
        self.assertEqual((r["energy_kwh"], r["good_total"], r["peak_interval_kw"]), (210, 280, 260))
        self.assertAlmostEqual(r["sec_kwh_per_good"], .75)
        self.assertEqual((r["baseline_kwh_same_mix"], r["difference_kwh"]), (195, -15))

    def test_reject_missing_duplicate(self):
        start, data = demo()
        for bad in (data[:-1], data[:-1] + [data[0]], data[1:]):
            with self.assertRaises(ValueError):
                summarize(bad, start, 4)

    def test_zero(self):
        start, _ = demo()
        r = summarize([Window(start, 0, 0, 0)], start, 1)
        self.assertIsNone(r["sec_kwh_per_good"])
        self.assertIsNone(r["load_factor"])

    def test_csv_and_bad_input(self):
        start, _ = demo()
        rows = from_records(csv.DictReader([",".join(FIELDS), f"{start.isoformat()},12.5,01,0"]))
        self.assertEqual(rows, [Window(start, 12.5, 1, 0)])
        with self.assertRaises(ValueError):
            from_records([{"start": "2026-11-25T08:00:00", "energy_kwh": 12, "good_a": 2, "good_b": 2}])

    def test_cumulative_reset(self):
        self.assertEqual(difference_kwh(1000, 1051), 51)
        with self.assertRaises(ValueError):
            difference_kwh(1051, 22)

    def test_reject_invalid_energy(self):
        start, _ = demo()
        for energy in (-1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                summarize([Window(start, energy, 3, 5)], start, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, help="UTF-8 CSV: start,energy_kwh,good_a,good_b")
    p.add_argument("--start", help="首區間開始；ISO 8601，必須含時區")
    p.add_argument("--periods", type=int, help="預期 15 分鐘筆數，不以收到的筆數推定")
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    if args.test:
        unittest.main(argv=["lab"])
    if args.csv:
        if not args.start or args.periods is None:
            p.error("--csv 需要 --start 與 --periods")
        with args.csv.open(encoding="utf-8-sig", newline="") as handle:
            rows = from_records(csv.DictReader(handle))
        result = summarize(rows, datetime.fromisoformat(args.start.replace("Z", "+00:00")), args.periods)
    else:
        if args.start or args.periods is not None:
            p.error("--start 與 --periods 僅與 --csv 共用")
        start, rows = demo()
        result = summarize(rows, start, 4)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
