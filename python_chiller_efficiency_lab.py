"""標準庫合成冰機能效練習；未連接設備，不做 IPLV/NPLV 評級。"""
from dataclasses import dataclass, fields
import argparse
import csv
import json
import math
from pathlib import Path
import unittest

KW_PER_RT = 12000 * 1055.05585262 / 3600 / 1000  # IT Btu/h to kW


@dataclass(frozen=True)
class Interval:
    duration_min: float
    flow_m3_h: float
    supply_c: float
    return_c: float
    rho_kg_m3: float
    cp_kj_kg_k: float
    chiller_kw: float
    aux_kw: float

    @property
    def cooling_kw(self):
        return (self.flow_m3_h / 3600 * self.rho_kg_m3 * self.cp_kj_kg_k
                * (self.return_c - self.supply_c))

    def validate(self):
        if not all(math.isfinite(getattr(self, f.name)) for f in fields(self)):
            raise ValueError("不接受非有限值")
        if min(self.duration_min, self.rho_kg_m3, self.cp_kj_kg_k) <= 0:
            raise ValueError("時間、密度與比熱必須大於零")
        if min(self.flow_m3_h, self.chiller_kw, self.aux_kw) < 0:
            raise ValueError("流量和用電量測不可為負")
        if self.return_c < self.supply_c:
            raise ValueError("回水低於供水；先核對感測器位置、模式與同時性")
        if self.cooling_kw > 0 and self.chiller_kw == 0:
            raise ValueError("此單機邊界不接受正冷量而冰機用電為零；核對邊界及時間窗")


SYNTHETIC = (
    Interval(15, 180, 7.0, 12, 1000, 4.186, 200, 35),
    Interval(30, 144, 7.5, 12, 1000, 4.186, 160, 30),
    Interval(45, 90, 7.0, 11, 1000, 4.186, 105, 25),
)


def kpis(cooling, electric):
    if cooling <= 0 or electric <= 0:
        return {"cop": None, "kw_per_rt": None}
    return {"cop": cooling / electric, "kw_per_rt": KW_PER_RT * electric / cooling}


def matched_summary(rows):
    cool_kwh = chiller_kwh = aux_kwh = 0.0
    detail = []
    for row in rows:
        row.validate()
        cooling = row.cooling_kw
        plant_kw = row.chiller_kw + row.aux_kw
        h = row.duration_min / 60
        cool_kwh += cooling * h
        chiller_kwh += row.chiller_kw * h
        aux_kwh += row.aux_kw * h
        detail.append({
            "cooling_kw": cooling, "cooling_rt": cooling / KW_PER_RT,
            "chiller": kpis(cooling, row.chiller_kw),
            "plant": kpis(cooling, plant_kw)
        })
    if not detail:
        raise ValueError("至少一筆有效的同步時段資料")
    return {
        "intervals": detail, "cooling_kwh": cool_kwh,
        "chiller_kwh": chiller_kwh, "aux_kwh": aux_kwh,
        "plant_kwh": chiller_kwh + aux_kwh,
        "chiller": kpis(cool_kwh, chiller_kwh),
        "plant": kpis(cool_kwh, chiller_kwh + aux_kwh),
    }


def electric_residual(chiller_kwh, aux_kwh, independently_metered_plant_kwh):
    """總表減去同一時間窗的分表合計；僅診斷，不自動調整讀值。"""
    if any(not math.isfinite(v) or v < 0 for v in
           (chiller_kwh, aux_kwh, independently_metered_plant_kwh)):
        raise ValueError("殘差檢查輸入必須是非負有限電能")
    diff = independently_metered_plant_kwh - chiller_kwh - aux_kwh
    return {"kwh": diff,
            "pct_of_total_meter": 100 * diff / independently_metered_plant_kwh
                                if independently_metered_plant_kwh else None}


def read_csv(path):
    schema = tuple(f.name for f in fields(Interval))
    with open(path, encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or set(reader.fieldnames) != set(schema) or len(reader.fieldnames) != len(schema):
            raise ValueError("CSV 欄位不符")
        for i, row in enumerate(reader, 2):
            try:
                if None in row:
                    raise ValueError("欄位過多")
                value = Interval(*(float(row[name]) for name in schema))
                value.validate()
            except (ValueError, TypeError) as err:
                raise ValueError(f"第 {i} 列不完整或無效") from err
            yield value


class LabTests(unittest.TestCase):
    def test_baseline(self):
        s = matched_summary(SYNTHETIC)
        self.assertAlmostEqual(s["intervals"][0]["cooling_kw"], 1046.5)
        self.assertAlmostEqual(s["cooling_kwh"], 952.315)
        self.assertAlmostEqual(s["plant_kwh"], 251.25)
        self.assertAlmostEqual(electric_residual(s["chiller_kwh"], s["aux_kwh"], 253)["kwh"], 1.75)

    def test_sign_and_zero(self):
        from dataclasses import replace
        first = SYNTHETIC[0]
        for bad in (replace(first, return_c=6),
                    replace(first, chiller_kw=0),
                    replace(first, flow_m3_h=math.nan)):
            with self.assertRaises(ValueError):
                matched_summary((bad,))
        zero = matched_summary((replace(first, flow_m3_h=0),))
        self.assertIsNone(zero["chiller"]["cop"])
        self.assertGreater(zero["plant_kwh"], 0)

    def test_missing_data(self):
        from tempfile import TemporaryDirectory
        with self.assertRaises(ValueError):
            matched_summary(())
        with TemporaryDirectory() as d:
            path = Path(d, "missing.csv")
            path.write_text("duration_min\n15\n")
            with self.assertRaises(ValueError):
                list(read_csv(path))
            path.write_text(",".join(f.name for f in fields(Interval))
                            + "\n15,180,7,,1000,4.186,200,35\n")
            with self.assertRaises(ValueError):
                list(read_csv(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="可選的同步合成資料 CSV")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        unittest.main(argv=["lab"])
        return
    s = matched_summary(read_csv(args.csv) if args.csv else SYNTHETIC)
    if not args.csv:
        s["synthetic_total_meter_residual"] = electric_residual(
            s["chiller_kwh"], s["aux_kwh"], 253
        )
    print(json.dumps(s, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
