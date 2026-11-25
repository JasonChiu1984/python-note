"""以合成 HVAC 日電量示範一元線性迴歸，僅用 Python 標準函式庫。"""
from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite, isclose
from statistics import mean
import argparse
import csv
import json
import unittest


@dataclass(frozen=True)
class Row:
    day: date
    outdoor_c: float
    cooling_kwh: float


def fixture():
    temperatures = [26, 27, 26.5, 29, 28, 27.5, 30, 31, 29.5, 30.5,
                    28.5, 27, 26.5, 32, 31, 30, 29, 28, 27.5, 30,
                    29.5, 31, 32, 29, 27.5, 30, 31.5, 33]
    noise = [-21, 6, -12, 18, 2, -14, 11, 23, -7, 14, -6, -3,
             4, 17, -12, 8, -13, 5, -7, 6, -5, 17, 9, -14, -2, 14, -6, 23]
    start = date(2026, 7, 1)
    return [Row(start + timedelta(days=i), x, 610 + 54 * (x - 26) + noise[i])
            for i, x in enumerate(temperatures)]


def load_csv(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"date", "outdoor_c", "cooling_kwh"}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("CSV 缺少 date、outdoor_c 或 cooling_kwh")
        for n, row in enumerate(reader, start=2):
            try:
                parsed = Row(date.fromisoformat(row["date"]),
                             float(row["outdoor_c"]), float(row["cooling_kwh"]))
                if not all(isfinite(v) for v in (parsed.outdoor_c, parsed.cooling_kwh)):
                    raise ValueError("不可為 NaN 或無窮大")
                if parsed.cooling_kwh < 0:
                    raise ValueError("每日耗電量不可為負")
            except (TypeError, ValueError) as exc:
                raise ValueError(f"第 {n} 列格式有誤：{exc}") from exc
            rows.append(parsed)
    return rows


@dataclass(frozen=True)
class Model:
    x0: float
    y0: float
    slope: float
    xmin: float
    xmax: float

    def predict(self, x):
        return self.y0 + self.slope * (x - self.x0)

    def outside_training(self, x):
        return not self.xmin <= x <= self.xmax


def fit(rows):
    if len(rows) < 2:
        raise ValueError("至少需要兩筆訓練資料")
    xs = [r.outdoor_c for r in rows]
    ys = [r.cooling_kwh for r in rows]
    x0, y0 = mean(xs), mean(ys)
    sxx = sum((x - x0) ** 2 for x in xs)
    if not sxx:
        raise ValueError("訓練溫度無變異，無法估計斜率")
    slope = sum((x - x0) * (y - y0) for x, y in zip(xs, ys)) / sxx
    return Model(x0, y0, slope, min(xs), max(xs))


def time_split(rows, test_size):
    ranked = sorted(rows, key=lambda r: r.day)
    if len({r.day for r in ranked}) != len(ranked):
        raise ValueError("每日資料須唯一；請先處理重複日期")
    if not 2 <= test_size <= len(ranked) - 2:
        raise ValueError("訓練與測試區間各至少需要兩筆")
    return ranked[:-test_size], ranked[-test_size:]


def score(observed, estimated):
    if not observed or len(observed) != len(estimated):
        raise ValueError("兩組資料須非空且同長度")
    residuals = [actual - pred for actual, pred in zip(observed, estimated)]
    center = mean(observed)
    sst = sum((y - center) ** 2 for y in observed)
    return {"mae_kwh_per_day": mean(abs(e) for e in residuals),
            "bias_actual_minus_prediction": mean(residuals),
            "r2": None if not sst else 1 - sum(e * e for e in residuals) / sst}


def evaluate(rows, test_size=8):
    train, test = time_split(rows, test_size)
    m = fit(train)
    actual = [r.cooling_kwh for r in test]
    predicted = [m.predict(r.outdoor_c) for r in test]
    return train, test, m, score(actual, predicted), score(actual, [m.y0] * len(test))


class Checks(unittest.TestCase):
    def test_fit_exact_line(self):
        d = date(2026, 1, 1)
        m = fit([Row(d, x, 100 + 12 * x) for x in (1, 2, 3)])
        self.assertTrue(isclose(m.slope, 12.0))
        self.assertTrue(isclose(m.predict(4), 148.0))
        self.assertTrue(m.outside_training(4))

    def test_constant_x_rejected(self):
        d = date(2026, 1, 1)
        with self.assertRaises(ValueError):
            fit([Row(d, 30, 10), Row(d, 30, 20)])

    def test_constant_target_r2_undefined(self):
        self.assertIsNone(score([2.0, 2.0], [2.0, 2.0])["r2"])

    def test_r2_can_be_negative(self):
        self.assertLess(score([2.0, 3.0], [1.0, 1.0])["r2"], 0)

    def test_holdout_and_baseline(self):
        train, test, m, result, baseline = evaluate(list(reversed(fixture())))
        self.assertLess(train[-1].day, test[0].day)
        self.assertEqual((len(train), len(test)), (20, 8))
        self.assertEqual(sum(m.outside_training(r.outdoor_c) for r in test), 1)
        self.assertLess(result["mae_kwh_per_day"], baseline["mae_kwh_per_day"])

    def test_duplicate_date_rejected(self):
        rows = fixture()
        with self.assertRaises(ValueError):
            time_split(rows + [rows[0]], 8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", help="自有 CSV：date,outdoor_c,cooling_kwh")
    parser.add_argument("--test-size", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
        return int(not result.wasSuccessful())
    try:
        train, test, m, metrics, baseline = evaluate(
            load_csv(args.csv) if args.csv else fixture(), args.test_size)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "source": "CSV" if args.csv else "合成資料，非場域實測",
        "train": [str(train[0].day), str(train[-1].day), len(train)],
        "test": [str(test[0].day), str(test[-1].day), len(test)],
        "x0_c": m.x0, "y0_kwh_per_day": m.y0, "slope_kwh_per_c_per_day": m.slope,
        "training_range_c": [m.xmin, m.xmax],
        "outside_training": [str(r.day) for r in test if m.outside_training(r.outdoor_c)],
        "metrics": metrics, "baseline": baseline,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
