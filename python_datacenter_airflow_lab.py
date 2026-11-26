"""機房氣流教學算例，僅用 Python 3.11+ 標準庫；不讀取、不控制任何設備。"""
from dataclasses import dataclass, asdict
from math import isfinite
import argparse
import json
import unittest

M3_PER_FT3 = 0.028316846592
CP_KJ_KG_K = 1.006  # 近室溫乾空氣的近似值


@dataclass(frozen=True)
class Airflow:
    heat_air_kw: float
    required_m3_s: float
    required_m3_h: float
    required_cfm: float
    gross_required_m3_h: float
    effective_supply_m3_h: float | None
    margin_m3_h: float | None


def airflow(
    it_kw: float,
    delta_t_k: float,
    *,
    direct_liquid_fraction: float = 0.0,
    extra_air_kw: float = 0.0,
    bypass_fraction: float = 0.0,
    density_kg_m3: float = 1.2,
    supply_m3_h: float | None = None,
) -> Airflow:
    """估算同一空氣邊界的穩態顯熱風量。旁通比例以該區總送風為分母。"""
    supplied = () if supply_m3_h is None else (supply_m3_h,)
    values = (it_kw, delta_t_k, direct_liquid_fraction, extra_air_kw,
              bypass_fraction, density_kg_m3, *supplied)
    if not all(isfinite(x) for x in values):
        raise ValueError("數值必須是有限值")
    if it_kw < 0 or extra_air_kw < 0 or any(x < 0 for x in supplied):
        raise ValueError("輸入功率和量測風量不可為負")
    if delta_t_k <= 0 or density_kg_m3 <= 0:
        raise ValueError("空氣溫升與密度必須大於零")
    if not 0 <= direct_liquid_fraction <= 1 or not 0 <= bypass_fraction < 1:
        raise ValueError("液冷比例須為 0–1；送風旁通比例須為 0（含）至 1（不含）")

    heat = it_kw * (1 - direct_liquid_fraction) + extra_air_kw
    required = heat / (density_kg_m3 * CP_KJ_KG_K * delta_t_k)
    required_h = 3600 * required
    gross_required = required_h / (1 - bypass_fraction)
    effective = None if supply_m3_h is None else supply_m3_h * (1 - bypass_fraction)
    margin = None if effective is None else effective - required_h
    return Airflow(heat, required, required_h, 60 * required / M3_PER_FT3,
                   gross_required, effective, margin)


class Tests(unittest.TestCase):
    def test_46_racks(self):
        r = airflow(46 * 8, 12, bypass_fraction=0.1, supply_m3_h=108_000)
        self.assertAlmostEqual(r.required_m3_h, 91_451.29, places=2)
        self.assertAlmostEqual(r.gross_required_m3_h, r.required_m3_h / 0.9)
        self.assertEqual(r.effective_supply_m3_h, 97_200)
        self.assertGreater(r.margin_m3_h, 0)

    def test_unchanged_load_less_supply(self):
        r = airflow(368, 12, bypass_fraction=0.1, supply_m3_h=90_000)
        self.assertLess(r.margin_m3_h, 0)

    def test_hybrid_heat_boundary(self):
        r = airflow(368, 12, direct_liquid_fraction=0.7, extra_air_kw=12)
        self.assertAlmostEqual(r.heat_air_kw, 122.4)
        self.assertIsNone(r.margin_m3_h)

    def test_cfm_conversion(self):
        r = airflow(8, 12)
        self.assertAlmostEqual(r.required_cfm * M3_PER_FT3 / 60, r.required_m3_s)

    def test_invalid_values(self):
        for field, value in (("it_kw", -1), ("delta_t_k", 0), ("delta_t_k", -1),
                             ("density_kg_m3", float("nan")), ("bypass_fraction", 1),
                             ("direct_liquid_fraction", 1.01), ("supply_m3_h", -1)):
            with self.subTest(field=field, value=value):
                values = dict(it_kw=8, delta_t_k=12)
                values[field] = value
                with self.assertRaises(ValueError):
                    airflow(**values)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--it-kw", type=float, default=368)
    p.add_argument("--delta-t-k", type=float, default=12)
    p.add_argument("--liquid-fraction", type=float, default=0.0)
    p.add_argument("--extra-air-kw", type=float, default=0.0)
    p.add_argument("--bypass", type=float, default=0.0)
    p.add_argument("--supply-m3-h", type=float)
    p.add_argument("--density", type=float, default=1.2)
    p.add_argument("--test", action="store_true")
    a = p.parse_args()
    if a.test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        return 0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1
    try:
        result = airflow(a.it_kw, a.delta_t_k, direct_liquid_fraction=a.liquid_fraction,
                         extra_air_kw=a.extra_air_kw, bypass_fraction=a.bypass,
                         density_kg_m3=a.density, supply_m3_h=a.supply_m3_h)
    except ValueError as err:
        p.error(str(err))
    print(json.dumps(asdict(result), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
