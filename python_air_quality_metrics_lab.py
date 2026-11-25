"""室內空氣品質遙測教學（Python 3.11+，純標準函式庫，無網路）。

把同目錄合成 CSV 放到腳本旁邊，執行：
    python3 python_air_quality_metrics_lab.py
    python3 python_air_quality_metrics_lab.py --self-test

各欄統計只使用有效樣本；空白不當 0，stale/bad 不沿用舊值。
數字範圍與覆蓋門檻只是本教材的資料契約，並非健康、法規或警報標準。
本程式不從室內資料推導任何官方 AQI。
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import statistics
from typing import Iterable, TextIO
import unittest


@dataclass(frozen=True)
class Metric:
    units: str
    low: float
    high: float


# 合成資料示範定義，不是室內安全範圍或感測器規格。
METRICS = {
    "co2_ppm": Metric("ppm", 250, 10_000),
    "pm25_ug_m3": Metric("µg/m³", 0, 5_000),
    "temp_c": Metric("°C", -40, 85),
    "rh_pct": Metric("%RH", 0, 100),
}
FIELDS = ("timestamp", *METRICS, "quality")
QUALITY = {"ok", "stale", "bad", "missing"}
STATES = ("valid", "missing", "stale", "bad", "invalid", "duplicate")
DEFAULT_START = "2026-11-25T10:00:00Z"
DEFAULT_END = "2026-11-25T10:30:00Z"
DEFAULT_SAMPLE = Path(__file__).with_name("python_air_quality_metrics_sample.csv")


@dataclass(frozen=True)
class Sample:
    timestamp: datetime
    quality: str
    values: dict[str, str]


def parse_time(text: str) -> datetime:
    """要求含時區的 ISO 8601 時刻；統一換算為 UTC。"""
    value = datetime.fromisoformat(text.strip())
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp 必須包含時區，例如 2026-11-25T10:00:00Z")
    return value.astimezone(timezone.utc)


def timestamp_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def read_samples(source: TextIO) -> Iterable[Sample]:
    reader = csv.DictReader(source)
    if reader.fieldnames != list(FIELDS):
        raise ValueError(f"CSV 欄位須依序為：{', '.join(FIELDS)}")
    for row in reader:
        number = reader.line_num
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"CSV 第 {number} 行欄位數錯誤")
        quality = row["quality"].strip()
        if quality not in QUALITY:
            raise ValueError(f"CSV 第 {number} 行 quality 必須為 ok/stale/bad/missing")
        try:
            timestamp = parse_time(row["timestamp"])
        except ValueError as exc:
            raise ValueError(f"CSV 第 {number} 行 timestamp 無效：{exc}") from exc
        yield Sample(timestamp, quality, {field: row[field] for field in METRICS})


def classify(value: str, metric: Metric) -> tuple[str, float | None]:
    value = value.strip()
    if not value:
        return "missing", None
    try:
        number = float(value)
    except ValueError:
        return "invalid", None
    if not math.isfinite(number) or not metric.low <= number <= metric.high:
        return "invalid", None
    return "valid", number


def summarize(
    samples: Iterable[Sample], start: datetime, end: datetime, *,
    interval_minutes: int = 5, min_coverage: float = 0.6,
) -> dict:
    """只使用半開時間窗 [start, end) 及從 start 對齊的定距格。"""
    if start.tzinfo is None or start.utcoffset() is None or end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("start 與 end 必須包含時區")
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if not isinstance(interval_minutes, int) or isinstance(interval_minutes, bool) or not 1 <= interval_minutes <= 1_440:
        raise ValueError("interval_minutes 必須是 1 到 1440 的整數")
    if not math.isfinite(min_coverage) or not 0 <= min_coverage <= 1:
        raise ValueError("min_coverage 必須是 0 到 1 的有限數字")
    step = timedelta(minutes=interval_minutes)
    span = end - start
    if span <= timedelta(0) or span % step != timedelta(0):
        raise ValueError("end 必須在 start 之後，且窗長必須整除格距")
    expected = span // step
    if expected > 100_000:
        raise ValueError("每次最多分析 100000 格")

    # Mappings only store aligned, in-window slots. Repeated aligned timestamps
    # make that whole slot ambiguous; do not silently choose first or last.
    slots: dict[datetime, Sample | None] = {}
    outside_rows = off_grid_rows = duplicate_rows = 0
    for row in samples:
        if row.timestamp.tzinfo is None or row.timestamp.utcoffset() is None:
            raise ValueError("sample timestamp 必須包含時區")
        time = row.timestamp.astimezone(timezone.utc)
        if row.quality not in QUALITY:
            raise ValueError(f"{timestamp_text(time)} quality 不在允許清單")
        if not start <= time < end:
            outside_rows += 1
        elif (time - start) % step != timedelta(0):
            off_grid_rows += 1
        elif time in slots:
            duplicate_rows += 1
            slots[time] = None
        else:
            slots[time] = row

    counters = {field: dict.fromkeys(STATES, 0) for field in METRICS}
    observed: dict[str, list[float]] = {field: [] for field in METRICS}
    latest: dict[str, tuple[datetime, float]] = {}
    for index in range(expected):
        t = start + index * step
        row = slots.get(t)
        for name, metric in METRICS.items():
            if row is None:
                state, number = ("duplicate" if t in slots else "missing"), None
            elif row.quality != "ok":
                state, number = row.quality, None
            else:
                state, number = classify(row.values.get(name, ""), metric)
            counters[name][state] += 1
            if number is not None:
                observed[name].append(number)
                latest[name] = (t, number)

    summary = {}
    for name, metric in METRICS.items():
        numbers = observed[name]
        last = latest.get(name)
        coverage = len(numbers) / expected
        summary[name] = {
            "units": metric.units,
            "coverage": round(coverage, 6),
            "coverage_ok": bool(numbers) and coverage >= min_coverage,
            "counts": counters[name],
            "observed_mean": round(statistics.fmean(numbers), 3) if numbers else None,
            "observed_min": min(numbers, default=None),
            "observed_max": max(numbers, default=None),
            "latest_valid_value": last[1] if last else None,
            "latest_valid_timestamp": timestamp_text(last[0]) if last else None,
            "latest_valid_age_seconds": (end - last[0]).total_seconds() if last else None,
        }
    return {
        "window": {
            "start_inclusive": timestamp_text(start),
            "end_exclusive": timestamp_text(end),
            "interval_minutes": interval_minutes,
            "expected": expected,
            "min_coverage": min_coverage,
        },
        "row_diagnostics": {
            "no_row_slots": expected - len(slots),
            "outside_window_rows": outside_rows,
            "off_grid_rows": off_grid_rows,
            "duplicate_extra_rows": duplicate_rows,
        },
        "metrics": summary,
        "note": (
            "合成遙測資料教學；observed_* 僅描述有效樣本，即使覆蓋不足仍不補值，"
            "不代表全窗暴露或健康／法規判斷，不計官方 AQI。"
        ),
    }


class MetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.start = parse_time(DEFAULT_START)
        cls.end = parse_time(DEFAULT_END)

    def sample(self, clock: str, quality: str = "ok", **values: str) -> Sample:
        fields = {"co2_ppm": "800", "pm25_ug_m3": "0", "temp_c": "24", "rh_pct": "49"}
        return Sample(parse_time(f"2026-11-25T{clock}:00Z"), quality, fields | values)

    def stats(self, rows, **kwargs):
        return summarize(rows, self.start, self.end, **kwargs)

    def test_fixture(self):
        with DEFAULT_SAMPLE.open(encoding="utf-8-sig", newline="") as f:
            result = self.stats(read_samples(f))
        self.assertEqual(result["row_diagnostics"]["no_row_slots"], 1)
        co2, pm = [result["metrics"][field] for field in ("co2_ppm", "pm25_ug_m3")]
        self.assertEqual(co2["counts"], {
            "valid": 4, "missing": 1, "stale": 1, "bad": 0, "invalid": 0, "duplicate": 0,
        })
        self.assertEqual(co2["observed_mean"], 837.5)
        self.assertEqual(co2["latest_valid_age_seconds"], 300)
        self.assertTrue(co2["coverage_ok"])
        self.assertEqual(pm["observed_mean"], 14.333)
        self.assertEqual(pm["counts"]["missing"], 2)
        self.assertEqual(pm["coverage"], 0.5)
        self.assertFalse(pm["coverage_ok"])

    def test_half_open_and_unordered(self):
        result = self.stats([
            self.sample("10:25"), self.sample("10:30"), self.sample("09:55"),
            self.sample("10:00"), self.sample("10:04"),
        ])
        self.assertEqual(result["row_diagnostics"], {
            "no_row_slots": 4, "outside_window_rows": 2, "off_grid_rows": 1,
            "duplicate_extra_rows": 0,
        })
        m = result["metrics"]["pm25_ug_m3"]
        self.assertEqual((m["counts"]["valid"], m["observed_min"]), (2, 0))
        self.assertEqual(m["latest_valid_timestamp"], "2026-11-25T10:25:00Z")

    def test_threshold_is_inclusive(self):
        row = self.sample("10:00")
        self.assertTrue(self.stats([row], min_coverage=1/6)["metrics"]["co2_ppm"]["coverage_ok"])
        self.assertFalse(self.stats([row], min_coverage=0.2)["metrics"]["co2_ppm"]["coverage_ok"])
        self.assertFalse(self.stats([], min_coverage=0)["metrics"]["co2_ppm"]["coverage_ok"])

    def test_invalid_and_missing_are_not_zero(self):
        result = self.stats([
            self.sample("10:00", co2_ppm="NaN", pm25_ug_m3="-1", temp_c="inf", rh_pct="100.1"),
            self.sample("10:05", co2_ppm="not a number", pm25_ug_m3="", temp_c="-41", rh_pct="0"),
            self.sample("10:10", co2_ppm="250", pm25_ug_m3="0", temp_c="85", rh_pct="100"),
        ])
        quality = result["metrics"]
        self.assertEqual(quality["co2_ppm"]["counts"]["invalid"], 2)
        self.assertEqual(quality["co2_ppm"]["observed_mean"], 250)
        self.assertEqual(quality["pm25_ug_m3"]["counts"]["invalid"], 1)
        self.assertEqual(quality["pm25_ug_m3"]["counts"]["missing"], 4)
        self.assertEqual(quality["pm25_ug_m3"]["observed_mean"], 0)
        self.assertEqual(quality["temp_c"]["observed_max"], 85)
        self.assertEqual(quality["rh_pct"]["observed_mean"], 50)

    def test_stale_bad_duplicate(self):
        result = self.stats([
            self.sample("10:00", "stale"), self.sample("10:05", "bad"),
            self.sample("10:10", "missing"), self.sample("10:15"),
            self.sample("10:15", co2_ppm="900"),
        ])
        counts = result["metrics"]["co2_ppm"]["counts"]
        self.assertEqual(counts, {
            "valid": 0, "missing": 3, "stale": 1, "bad": 1, "invalid": 0, "duplicate": 1,
        })
        self.assertIsNone(result["metrics"]["co2_ppm"]["observed_mean"])
        self.assertEqual(result["row_diagnostics"]["duplicate_extra_rows"], 1)

    def test_window_validation(self):
        for interval in (0, -5, 7):
            with self.assertRaises(ValueError):
                self.stats([], interval_minutes=interval)
        with self.assertRaises(ValueError):
            self.stats([], min_coverage=float("nan"))
        with self.assertRaises(ValueError):
            summarize([], self.end, self.start)
        with self.assertRaises(ValueError):
            parse_time("2026-11-25T10:00:00")
        self.assertEqual(parse_time("2026-11-25T18:00:00+08:00"), self.start)

    def test_csv_header_and_quality(self):
        from io import StringIO

        with self.assertRaises(ValueError):
            list(read_samples(StringIO("timestamp,co2_ppm\n")))
        header = ",".join(FIELDS) + "\n"
        with self.assertRaisesRegex(ValueError, "quality"):
            list(read_samples(StringIO(header + "2026-11-25T10:00:00Z,700,9,24,55,suspicious\n")))
        with self.assertRaisesRegex(ValueError, "欄位數"):
            list(read_samples(StringIO(header + "2026-11-25T10:00:00Z,700,9\n")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path, nargs="?", default=DEFAULT_SAMPLE)
    parser.add_argument("--start", default=DEFAULT_START, help="分析窗起點（包含；含時區）")
    parser.add_argument("--end", default=DEFAULT_END, help="分析窗終點（排除；含時區）")
    parser.add_argument("--interval-minutes", type=int, default=5)
    parser.add_argument("--min-coverage", type=float, default=0.6, help="本教材資料足量門檻 0–1")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(MetricsTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    try:
        with args.csv.open(encoding="utf-8-sig", newline="") as f:
            result = summarize(
                read_samples(f), parse_time(args.start), parse_time(args.end),
                interval_minutes=args.interval_minutes, min_coverage=args.min_coverage,
            )
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(status=2, message=f"無法產生統計：{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
