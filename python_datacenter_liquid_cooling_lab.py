"""液冷機房同窗熱量與用電試算；Python 3.11+、標準庫、合成資料。"""
import argparse
from dataclasses import dataclass, replace
import json
from math import isfinite, isclose, log
import unittest

RT_KW = 3.516853


@dataclass(frozen=True)
class Loop:
    m3_h: float
    supply_c: float
    return_c: float
    density_kg_m3: float = 1000.0  # 教學用純水近似
    cp_kj_kg_k: float = 4.186

    def __post_init__(self):
        values = (self.m3_h, self.supply_c, self.return_c,
                  self.density_kg_m3, self.cp_kj_kg_k)
        if not all(isfinite(x) for x in values):
            raise ValueError("水側讀值必須是有限數")
        if self.m3_h < 0 or self.density_kg_m3 <= 0 or self.cp_kj_kg_k <= 0:
            raise ValueError("流量不可為負，密度與比熱必須大於零")

    @property
    def delta_k(self):
        return self.return_c - self.supply_c

    @property
    def heat_kw(self):
        # kJ/s 就是 kW；保留負號，不能取 abs 後算成移熱。
        return self.m3_h / 3600 * self.density_kg_m3 * self.cp_kj_kg_k * self.delta_k


@dataclass(frozen=True)
class Window:
    hours: float
    it_kw: float
    tcs: Loop
    fws: Loop
    cdu_kw: float
    pump_kw: float

    def __post_init__(self):
        values = (self.hours, self.it_kw, self.cdu_kw, self.pump_kw)
        if not all(isfinite(x) and x >= 0 for x in values) or self.hours == 0:
            raise ValueError("時間必須為正，功率必須為非負有限數")
        if self.pump_kw > self.cdu_kw:
            raise ValueError("同邊界泵分表不可大於 CDU 整機輸入")


def ratio(a, b):
    return a / b if b > 0 else None


def terminal_approaches(tcs, fws):
    """逆流液對液換熱器的兩個端點逼近溫差，不是水側 ΔT。"""
    return tcs.supply_c - fws.supply_c, tcs.return_c - fws.return_c


def lmtd(cold_end_k, hot_end_k):
    if not all(isfinite(x) and x > 0 for x in (cold_end_k, hot_end_k)):
        raise ValueError("此簡化逆流 LMTD 公式要求兩端溫差皆為正")
    if isclose(cold_end_k, hot_end_k):
        return (cold_end_k + hot_end_k) / 2
    return (hot_end_k - cold_end_k) / log(hot_end_k / cold_end_k)


def summarize(windows, requested_hours, *, tcs_represents_it_heat=False):
    """只加總配對且可比的合成視窗；不以零補缺，不宣稱已完整計量。"""
    if not isfinite(requested_hours) or requested_hours <= 0:
        raise ValueError("指定期間須為正的有限小時數")
    observed = valid = it = tcs = fws = cdu = pump = 0.0
    rows = []
    for w in windows:
        observed += w.hours
        t, f = w.tcs.heat_kw, w.fws.heat_kw
        if not all(isfinite(x) for x in (t, f)):
            raise ValueError("移熱量超出可表示範圍")
        a, b = terminal_approaches(w.tcs, w.fws)
        # 教學只接受正向運轉資料，不代表停機等其他合法狀態可丟棄。
        ok = t > 0 and f > 0 and a > 0 and b > 0
        rows.append({"included": ok, "tcs_kw": t, "fws_kw": f,
                     "cold_end_approach_k": a, "hot_end_approach_k": b,
                     "lmtd_k": lmtd(a, b) if ok else None})
        if not ok:
            continue
        valid += w.hours
        it += w.it_kw * w.hours
        tcs += t * w.hours
        fws += f * w.hours
        cdu += w.cdu_kw * w.hours
        pump += w.pump_kw * w.hours
    if observed > requested_hours and not isclose(observed, requested_hours):
        raise ValueError("樣本時數大於指定期間；先檢查重疊或重複窗")
    complete = isclose(valid, requested_hours)
    share = ratio(tcs, it) if complete and tcs_represents_it_heat else None
    # 熱量超過 IT 時保留原比值以便對帳，但不將負差寫成氣冷需求。
    return {"intervals": rows,
            "paired_coverage": valid / requested_hours,
            "complete": complete,
            "it_kwh_valid": it, "tcs_kwh_th_valid": tcs, "fws_kwh_th_valid": fws,
            "cdu_kwh_valid": cdu, "pump_kwh_valid": pump,
            "tcs_assumed_to_represent_it_heat": tcs_represents_it_heat,
            "estimated_liquid_capture_ratio": share,
            "estimated_air_residual_kwh_th": it - tcs if share is not None and share <= 1 else None,
            "capture_out_of_range": share is not None and share > 1,
            "fws_minus_tcs_kwh_th": fws - tcs if complete else None,
            "cdu_kwh_per_kwh_th": ratio(cdu, tcs) if complete else None,
            "pump_kwh_per_mwh_th": 1000 * pump / tcs if complete and tcs > 0 else None}


def facility_examples():
    """合成電力、水、排放、回收的同窗教學比值，不是正式 ISO 報表。"""
    it, facility, zone_it, zone_total = 250, 300, 150, 170
    water_l, grid_kwh, grid_ef, useful_export_kwh = 180, 300, 0.45, 40
    plant_input_kwh, evaporator_kwh_th = 36, 180
    return {
        "period_facility_to_it": facility / it,
        "zone_partial_pue_example": zone_total / zone_it,
        "onsite_water_l_per_kwh_it": water_l / it,
        "electricity_only_kgco2e_per_kwh_it": grid_kwh * grid_ef / it,
        "useful_export_to_facility_energy": useful_export_kwh / facility,
        "chilled_water_plant_kw_per_rt": plant_input_kwh * RT_KW / evaporator_kwh_th,
    }


DEMO = (
    Window(0.5, 120, Loop(10, 30, 38), Loop(10, 27, 35.2), 2.5, 2),
    Window(1.0, 190, Loop(14, 32, 42), Loop(14, 28, 38.2), 3.5, 3),
)


class Tests(unittest.TestCase):
    def test_heat_and_units(self):
        self.assertAlmostEqual(Loop(36, 20, 30).heat_kw, 418.6)
        self.assertAlmostEqual(Loop(36, 30, 20).heat_kw, -418.6)

    def test_interval_integration_and_capture(self):
        r = summarize(DEMO, 1.5, tcs_represents_it_heat=True)
        self.assertEqual(r["it_kwh_valid"], 250)
        self.assertAlmostEqual(r["tcs_kwh_th_valid"], 209.3)
        self.assertAlmostEqual(r["estimated_liquid_capture_ratio"], 0.8372)
        self.assertAlmostEqual(r["estimated_air_residual_kwh_th"], 40.7)
        self.assertAlmostEqual(r["fws_minus_tcs_kwh_th"], 4.4185555556)
        self.assertAlmostEqual(r["cdu_kwh_per_kwh_th"], 4.75 / 209.3)
        self.assertAlmostEqual(r["pump_kwh_per_mwh_th"], 4000 / 209.3)

    def test_approach(self):
        self.assertEqual(terminal_approaches(DEMO[0].tcs, DEMO[0].fws)[0], 3)
        self.assertEqual(lmtd(4, 4), 4)
        with self.assertRaises(ValueError):
            lmtd(0, 4)

    def test_missing_and_reverse_do_not_pass(self):
        valid = DEMO[0]
        reverse = replace(DEMO[1], tcs=Loop(14, 42, 32))
        for rows in ((valid,), (valid, reverse)):
            r = summarize(rows, 1.5, tcs_represents_it_heat=True)
            self.assertAlmostEqual(r["paired_coverage"], 1 / 3)
            self.assertFalse(r["complete"])
            self.assertIsNone(r["estimated_liquid_capture_ratio"])

    def test_above_unity_is_flagged_not_clipped(self):
        r = summarize((replace(DEMO[0], it_kw=50),), 0.5, tcs_represents_it_heat=True)
        self.assertTrue(r["capture_out_of_range"])
        self.assertGreater(r["estimated_liquid_capture_ratio"], 1)
        self.assertIsNone(r["estimated_air_residual_kwh_th"])

    def test_unverified_tcs_boundary_suppresses_it_capture(self):
        r = summarize(DEMO, 1.5)
        self.assertTrue(r["complete"])
        self.assertIsNone(r["estimated_liquid_capture_ratio"])
        self.assertIsNone(r["estimated_air_residual_kwh_th"])

    def test_zero_it_ratio_is_null(self):
        r = summarize((replace(DEMO[0], it_kw=0),), 0.5, tcs_represents_it_heat=True)
        self.assertIsNone(r["estimated_liquid_capture_ratio"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            Loop(-1, 20, 30)
        with self.assertRaises(ValueError):
            replace(DEMO[0], pump_kw=10)
        with self.assertRaises(ValueError):
            summarize(DEMO, 1)

    def test_facility_examples(self):
        r = facility_examples()
        self.assertAlmostEqual(r["period_facility_to_it"], 1.2)
        self.assertAlmostEqual(r["chilled_water_plant_kw_per_rt"], 0.7033706)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true", help="執行離線單元測試")
    args = p.parse_args()
    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    # 合成案例假設 TCS 表可代表 IT 捕熱，額外泵熱及熱蓄積皆已排除或可忽略。
    r = summarize(DEMO, requested_hours=1.5, tcs_represents_it_heat=True)
    print(json.dumps({"liquid": r, "facility": facility_examples()},
                     ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
