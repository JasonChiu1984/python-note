"""額外分表算例，與基本教材共用原四個 UTC 視窗。純合成、不連設備。"""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import sys
import unittest

STEP = timedelta(minutes=15)
START = datetime(2026, 7, 1, tzinfo=timezone.utc)
# 單位是資料契約的一部分，不嘗試推測錯標的單位。
UNITS = ("kWh", "L", "kgCO2e/kWh", "kgCO2e")

@dataclass(frozen=True)
class Row:
    start: datetime
    it: D
    facility: D
    cooling: D
    ups_in: D
    ups_out: D
    hall_it: D
    hall_total: D
    water_consumed: D
    water_in: D
    ef: D
    direct_co2e: D

ROWS = tuple(Row(START + i * STEP, *map(D, values.split())) for i, values in enumerate((
    "100 150 36 108 100 40 50 160 190 0.40 1",
    "200 260 40 209 200 75 89 220 260 0.35 0",
    "150 225 55 160 150 55 73 190 220 0.38 0",
    "250 300 33 258 250 90 102 280 330 0.42 2",
)))

def calculate(rows, start, end, units=UNITS):
    if tuple(units) != UNITS:
        raise ValueError("單位不符，應先明確轉換")
    if any(t.tzinfo != timezone.utc or t.minute % 15 or t.second or t.microsecond
           for t in (start, end)) or end <= start:
        raise ValueError("只接受正長度、UTC 四分之一小時對齊視窗")
    rows = tuple(rows)
    expected = {start + n * STEP for n in range((end - start) // STEP)}
    actual = {r.start for r in rows}
    if len(rows) != len(actual) or actual != expected:
        raise ValueError("視窗重複、缺漏或跨界")
    for r in rows:
        vals = tuple(getattr(r, k) for k in Row.__dataclass_fields__ if k != "start")
        if any(not isinstance(v, D) or not v.is_finite() or v < 0 for v in vals):
            raise ValueError("資料缺值、型別錯誤、負值或非有限值")
        if r.ups_out != r.it or r.ups_in < r.ups_out:
            raise ValueError("本無旁路算例需驗證 UPS 邊界")
        if r.facility < r.ups_in + r.cooling:
            raise ValueError("全站小於不重疊分表總量")
        if not (r.hall_it <= r.it and r.hall_it <= r.hall_total <= r.facility
                and r.hall_total - r.hall_it <= r.facility - r.it
                and r.water_consumed <= r.water_in):
            raise ValueError("子邊界或水量收支不合理")
    sums = {k: sum((getattr(r, k) for r in rows), D(0))
            for k in Row.__dataclass_fields__ if k != "start" and k != "ef"}
    def ratio(n, d):
        return n / d if d > 0 else None

    it, fac = sums["it"], sums["facility"]
    grid_carbon = sum(r.facility * r.ef for r in rows)
    return {
        **sums,
        "grid_carbon": grid_carbon,
        "other_energy": fac - sums["ups_in"] - sums["cooling"],
        "ipue": ratio(fac, it), "dcie": ratio(it, fac),
        "ppue": ratio(sums["hall_total"], sums["hall_it"]),
        "wue_consumption": ratio(sums["water_consumed"], it),
        "wue_input": ratio(sums["water_in"], it),
        "electricity_only_cue": ratio(grid_carbon, it),
        "broader_site_ghg_intensity": ratio(grid_carbon + sums["direct_co2e"], it),
        "cooling_share": ratio(sums["cooling"], fac),
        "ups_efficiency": ratio(sums["ups_out"], sums["ups_in"]),
    }

def rack_utilization(measured_kw, capacity_kw):
    if any(not isinstance(v, D) or not v.is_finite() for v in (measured_kw, capacity_kw)) or measured_kw < 0 or capacity_kw <= 0:
        raise ValueError("需要非負實測 kW 及正的核定可用 kW")
    return measured_kw / capacity_kw

class TestDetail(unittest.TestCase):
    def test_totals(self):
        a = calculate(ROWS, START, START + 4*STEP)
        for k,v in {"it":700,"facility":935,"cooling":164,"ups_in":735,"ups_out":700,
                    "other_energy":36,"hall_it":260,"hall_total":314,"water_consumed":850,
                    "water_in":1000,"direct_co2e":3}.items():
            self.assertEqual(a[k],v)
        self.assertEqual(a["grid_carbon"], D("362.50"))
        self.assertEqual(a["ipue"] * a["dcie"], D(1))

    def test_weighted(self):
        a = calculate(ROWS[:1], START, START+STEP)
        b = calculate(ROWS[1:], START+STEP, START+4*STEP)
        c = calculate(ROWS, START, START+4*STEP)
        self.assertNotEqual((a["ipue"]+b["ipue"])/2,c["ipue"])
        self.assertEqual((a["facility"]+b["facility"])/(a["it"]+b["it"]),c["ipue"])

    def test_quality(self):
        for rows in (ROWS[1:], ROWS + ROWS[:1], (replace(ROWS[0], it=None),*ROWS[1:]),
                     (replace(ROWS[0], water_in=D("NaN")) ,*ROWS[1:]),
                     (replace(ROWS[0], facility=D(140)),*ROWS[1:])):
            with self.assertRaises(ValueError):
                calculate(rows,START,START+4*STEP)
        with self.assertRaises(ValueError):
            calculate(ROWS,START,START+4*STEP,("Wh",*UNITS[1:]))

    def test_zero_and_rack(self):
        zero = Row(START, *[D(0)]*11)
        a = calculate([zero], START, START+STEP)
        self.assertIsNone(a["ipue"])
        self.assertIsNone(a["ups_efficiency"])
        self.assertEqual(rack_utilization(D(9), D(16)),D(".5625"))
        with self.assertRaises(ValueError):
            rack_utilization(D(9), D(0))

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        for label, rows, start, end in (
            ("15 min", ROWS[:1], START, START+STEP),
            ("45 min", ROWS[1:], START+STEP, START+4*STEP),
            ("60 min", ROWS, START, START+4*STEP)):
            print(label)
            for key, value in calculate(rows,start,end).items():
                print(f"  {key}: {value:.6f}" if value is not None else f"  {key}: N/A")
        print("rack load ratio =",rack_utilization(D(9),D(16)))
