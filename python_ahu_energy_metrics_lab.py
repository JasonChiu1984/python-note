#!/usr/bin/env python3
"""Offline air-handling unit example. SI units; no device I/O."""
import argparse
import json
import math
import unittest

KW_PER_RT = 3.516852842


def moist_air_enthalpy(t_c: float, w_kg_per_kg_da: float) -> float:
    """Return kJ per kg of dry air, near ordinary HVAC conditions."""
    if not math.isfinite(t_c) or not math.isfinite(w_kg_per_kg_da) or w_kg_per_kg_da < 0:
        raise ValueError("finite temperature and non-negative humidity ratio required")
    return 1.006 * t_c + w_kg_per_kg_da * (2501 + 1.86 * t_c)


def ahu_kpis(*, supply_m3h: float, m_da_kg_s: float, supply_kw: float,
             return_kw: float, fan_static_pa: float, filter_pa: float,
             t_enter_c: float, w_enter: float, t_leave_c: float, w_leave: float,
             t_reheat_c: float, water_m3h: float, water_supply_c: float,
             water_return_c: float, hours: float) -> dict[str, float]:
    """Steady cooling + sensible reheat snapshot, fresh water only."""
    values = (supply_m3h, m_da_kg_s, supply_kw, return_kw, fan_static_pa, filter_pa,
              t_enter_c, w_enter, t_leave_c, w_leave, t_reheat_c, water_m3h,
              water_supply_c, water_return_c, hours)
    if not all(map(math.isfinite, values)):
        raise ValueError("all measurements must be finite")
    if min(supply_m3h, m_da_kg_s, supply_kw, water_m3h, hours) <= 0:
        raise ValueError("positive airflow, fan power, water flow and duration required")
    if min(return_kw, fan_static_pa, filter_pa, w_enter, w_leave) < 0:
        raise ValueError("negative power, pressure or humidity ratio")
    if t_enter_c <= t_leave_c or w_enter < w_leave or t_reheat_c < t_leave_c:
        raise ValueError("expected cooling/dehumidifying coil followed by sensible reheat")
    if water_return_c <= water_supply_c:
        raise ValueError("cooling-water return must be warmer here")
    q_m3_s = supply_m3h / 3600
    fan_kw = supply_kw + return_kw
    static_eff = q_m3_s * fan_static_pa / (1000 * supply_kw)
    if static_eff > 1:
        raise ValueError("fan air power exceeds input; check measurement boundary and units")
    h_in = moist_air_enthalpy(t_enter_c, w_enter)
    h_out = moist_air_enthalpy(t_leave_c, w_leave)
    air_kw = m_da_kg_s * (h_in - h_out)
    water_kw = water_m3h / 3600 * 1000 * 4.186 * (water_return_c - water_supply_c)
    reheat_kw = m_da_kg_s * (moist_air_enthalpy(t_reheat_c, w_leave) - h_out)
    rt = air_kw / KW_PER_RT
    return {
        "supply_m3_s": q_m3_s, "fan_kwh_e": fan_kw * hours,
        "sfp_kw_per_m3_s": fan_kw / q_m3_s, "fan_static_wire_to_air_pct": static_eff * 100,
        "filter_air_power_kw": q_m3_s * filter_pa / 1000,
        "h_enter_kj_per_kg_da": h_in, "h_leave_kj_per_kg_da": h_out,
        "air_cooling_kw_th": air_kw, "water_cooling_kw_th": water_kw,
        "cooling_balance_pct_of_water": (air_kw - water_kw) / water_kw * 100,
        "air_cooling_rt": rt, "fan_kw_e_per_rt": fan_kw / rt,
        "condensate_est_kg_h": m_da_kg_s * (w_enter - w_leave) * 3600,
        "reheat_kw_th": reheat_kw, "reheat_kwh_th": reheat_kw * hours,
    }


DEMO = dict(supply_m3h=18000, m_da_kg_s=5.8, supply_kw=6, return_kw=2,
            fan_static_pa=650, filter_pa=150, t_enter_c=26, w_enter=.012,
            t_leave_c=13, w_leave=.0092, t_reheat_c=18, water_m3h=13,
            water_supply_c=6, water_return_c=14, hours=8)


class Tests(unittest.TestCase):
    def test_enthalpy(self):
        self.assertAlmostEqual(moist_air_enthalpy(26, .012), 56.74832)
        self.assertAlmostEqual(moist_air_enthalpy(13, .0092), 36.309656)

    def test_fan(self):
        r = ahu_kpis(**DEMO)
        for key, value in {"supply_m3_s": 5, "fan_kwh_e": 64, "sfp_kw_per_m3_s": 1.6,
                           "fan_static_wire_to_air_pct": 54.1666666667,
                           "filter_air_power_kw": .75}.items():
            self.assertAlmostEqual(r[key], value)

    def test_coil(self):
        r = ahu_kpis(**DEMO)
        self.assertAlmostEqual(r["air_cooling_kw_th"], 118.5442512)
        self.assertAlmostEqual(r["water_cooling_kw_th"], 120.928888889)
        self.assertAlmostEqual(r["condensate_est_kg_h"], 58.464)
        self.assertAlmostEqual(r["reheat_kw_th"], 29.670248)

    def test_invalid_quality_inputs(self):
        for patch in (dict(supply_m3h=0), dict(w_leave=.014), dict(water_return_c=5),
                      dict(fan_static_pa=3000), dict(hours=float("nan"))):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                ahu_kpis(**(DEMO | patch))

    def test_no_reheat_and_no_condensate(self):
        r = ahu_kpis(**(DEMO | {"t_reheat_c": 13, "w_enter": .0092}))
        self.assertEqual(r["reheat_kw_th"], 0)
        self.assertEqual(r["condensate_est_kg_h"], 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    if parser.parse_args().test:
        unittest.main(argv=[__file__], verbosity=2)
    else:
        print(json.dumps(ahu_kpis(**DEMO), indent=2))
