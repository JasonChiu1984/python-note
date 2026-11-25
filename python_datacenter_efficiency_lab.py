"""機房能效指標：15 分鐘合成區間，Python 3.11+，只用標準函式庫。"""
import argparse
import csv
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
import json
import unittest

STEP = timedelta(minutes=15)
START = "2026-07-01T00:00:00Z"
END = "2026-07-01T01:00:00Z"
FIELDS = ("timestamp_utc", "it_kwh", "facility_kwh", "water_l", "ef_kgco2e_per_kwh")
FIXTURE = """timestamp_utc,it_kwh,facility_kwh,water_l,ef_kgco2e_per_kwh
2026-07-01T00:00:00Z,100,150,160,0.40
2026-07-01T00:15:00Z,200,260,220,0.35
2026-07-01T00:30:00Z,150,225,190,0.38
2026-07-01T00:45:00Z,250,300,280,0.42
"""


@dataclass(frozen=True)
class Interval:
    at: datetime
    it_kwh: Decimal
    facility_kwh: Decimal
    water_l: Decimal
    factor: Decimal


def utc_quarter(raw):
    at = datetime.fromisoformat(raw)
    if at.tzinfo is None or at.utcoffset() != timedelta(0):
        raise ValueError("時間必須明確為 UTC（Z 或 +00:00）")
    if at.minute % 15 or at.second or at.microsecond:
        raise ValueError("時間須落在 15 分鐘刻度")
    return at.astimezone(timezone.utc)


def number(raw):
    value = Decimal(raw)
    if not value.is_finite() or value < 0:
        raise ValueError("數值必須有限、不可為負")
    return value


def read_intervals(handle):
    reader = csv.DictReader(handle)
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not set(FIELDS).issubset(fields):
        raise ValueError("CSV 欄名重複或缺少必要欄位：" + ",".join(FIELDS))
    rows = []
    for line, row in enumerate(reader, 2):
        try:
            if None in row:
                raise ValueError("欄位數超出標頭")
            rows.append(Interval(utc_quarter(row[FIELDS[0]]),
                                 *(number(row[key]) for key in FIELDS[1:])))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError(f"CSV 第 {line} 列無效：{error}") from error
    return rows


def report(rows, start, end):
    if end <= start:
        raise ValueError("end 必須晚於 start")
    current = start
    it = facility = water = carbon = Decimal(0)
    for row in sorted(rows, key=lambda row: row.at):
        if not start <= row.at < end:
            raise ValueError("有區間超出 [start, end)；請先只匯出所需期間")
        if row.at < current:
            raise ValueError(f"時間重複：{row.at.isoformat()}")
        if row.at > current:
            raise ValueError(f"區間缺漏：{current.isoformat()}")
        # 本案例的 facility 是完整場域正向用電，且包含同期間 IT。
        if row.facility_kwh < row.it_kwh:
            raise ValueError(f"總用電低於 IT：{row.at.isoformat()}，請核對量測邊界")
        it += row.it_kwh
        facility += row.facility_kwh
        water += row.water_l
        carbon += row.facility_kwh * row.factor
        current += STEP
    if current != end:
        raise ValueError(f"區間缺漏：{current.isoformat()}")
    if not it:
        raise ValueError("IT 總用電為 0，三個比值未定義")
    return {
        "start_utc": start.isoformat(),
        "end_exclusive_utc": end.isoformat(),
        "intervals": len(rows),
        "it_kwh": it,
        "facility_kwh": facility,
        "onsite_water_l": water,
        "illustrative_electricity_only_kgco2e": carbon,
        "pue_kwh_per_kwh_it": facility / it,
        "onsite_wue_l_per_kwh_it": water / it,
        "illustrative_electricity_only_cue_kgco2e_per_kwh_it": carbon / it,
    }


def thermal_demo():
    # 同一個水側與電表對應時點的示範。常溫純水近似，不適用未校正的乙二醇。
    flow_lps, supply_c, return_c, electrical_kw = map(Decimal, ("60", "7", "13", "270"))
    delta_t = return_c - supply_c
    cooling_kw = flow_lps * Decimal("1.0") * Decimal("4.186") * delta_t
    cooling_rt = cooling_kw / Decimal("3.51685")
    return {"flow_lps": flow_lps, "supply_c": supply_c, "return_c": return_c,
            "delta_t_c": delta_t, "cooling_kw": cooling_kw,
            "cooling_rt": cooling_rt, "electric_kw": electrical_kw,
            "electrical_kw_per_rt": electrical_kw / cooling_rt}


class TestLab(unittest.TestCase):
    def setUp(self):
        self.rows = read_intervals(StringIO(FIXTURE))
        self.start, self.end = utc_quarter(START), utc_quarter(END)

    def calculate(self, rows):
        return report(rows, self.start, self.end)

    def test_totals_then_ratios(self):
        result = self.calculate(self.rows)
        self.assertEqual(result["it_kwh"], 700)
        self.assertEqual(result["facility_kwh"], 935)
        self.assertEqual(result["onsite_water_l"], 850)
        self.assertEqual(result["illustrative_electricity_only_kgco2e"], Decimal("362.5"))
        self.assertEqual(result["pue_kwh_per_kwh_it"], Decimal(935) / 700)
        self.assertEqual(result["onsite_wue_l_per_kwh_it"], Decimal(850) / 700)
        self.assertEqual(result["illustrative_electricity_only_cue_kgco2e_per_kwh_it"],
                         Decimal("362.5") / 700)
        ratios = [r.facility_kwh / r.it_kwh for r in self.rows]
        self.assertNotEqual(result["pue_kwh_per_kwh_it"], sum(ratios) / len(ratios))

    def test_missing_first_middle_last(self):
        for skipped in (0, 1, 3):
            with self.subTest(skipped=skipped), self.assertRaisesRegex(ValueError, "缺漏"):
                self.calculate(self.rows[:skipped] + self.rows[skipped + 1:])

    def test_repeat_rejected_unsorted_accepted(self):
        self.assertEqual(self.calculate(self.rows[::-1]), self.calculate(self.rows))
        with self.assertRaisesRegex(ValueError, "重複"):
            self.calculate(self.rows + self.rows[:1])

    def test_zero_denominator(self):
        with self.assertRaisesRegex(ValueError, "未定義"):
            self.calculate([replace(r, it_kwh=Decimal(0)) for r in self.rows])

    def test_zero_it_on_one_interval_still_counts_facility_energy(self):
        rows = [replace(self.rows[0], it_kwh=Decimal(0))] + self.rows[1:]
        r = self.calculate(rows)
        self.assertEqual(r["facility_kwh"], 935)
        self.assertEqual(r["it_kwh"], 600)

    def test_bad_boundary(self):
        with self.assertRaisesRegex(ValueError, "總用電低於 IT"):
            self.calculate([replace(self.rows[0], facility_kwh=Decimal(99))] + self.rows[1:])

    def test_nonfinite_negative_missing(self):
        for bad in ("NaN", "Inf", "-1", ""):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "第 2 列"):
                read_intervals(StringIO(FIXTURE.replace(",100,", f",{bad},", 1)))

    def test_invalid_alignment(self):
        for raw in ("2026-07-01T00:00:00", "2026-07-01T00:00:00+08:00",
                    "2026-07-01T00:01:00Z"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                utc_quarter(raw)

    def test_thermal_snapshot(self):
        t = thermal_demo()
        self.assertEqual(t["delta_t_c"], 6)
        self.assertEqual(t["cooling_kw"], Decimal("1506.9600"))
        self.assertEqual(round(t["electrical_kw_per_rt"], 3), Decimal("0.630"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--csv", help="自訂對齊區間 CSV")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--thermal-demo", action="store_true")
    parser.add_argument("--start", help="UTC 期間起點，含")
    parser.add_argument("--end", help="UTC 期間終點，不含")
    args = parser.parse_args()
    if args.csv and not (args.start and args.end):
        parser.error("--csv 必須同時指定 --start 與 --end，才能檢查首尾缺漏")
    if not args.csv and (args.start or args.end):
        parser.error("--start 與 --end 只能與 --csv 一起使用")
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLab)
        return int(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    try:
        if args.thermal_demo:
            out = {"source": "合成冷卻快照，非現場量測", **thermal_demo()}
        elif args.csv:
            with open(args.csv, encoding="utf-8-sig", newline="") as handle:
                out = {"source": "CSV；來源與邊界須自行核實", **report(
                    read_intervals(handle), utc_quarter(args.start), utc_quarter(args.end))}
        else:
            out = {"source": "合成區間，非現場量測", **report(
                read_intervals(StringIO(FIXTURE)), utc_quarter(START), utc_quarter(END))}
    except (OSError, ValueError, ArithmeticError) as error:
        parser.error(str(error))
    # Decimal 以 JSON 字串輸出，以免轉成 binary float 損失精度。
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
