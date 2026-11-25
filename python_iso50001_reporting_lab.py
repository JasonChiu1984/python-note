"""ISO 50001 能源報表的合成例題；Python 3.10+，不代表標準指定模板。"""
from argparse import ArgumentParser
from decimal import Decimal, InvalidOperation
import json
import unittest

D = Decimal


def nonnegative(value, name):
    try:
        n = D(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} 不是有效十進位數") from exc
    if not n.is_finite() or n < 0:
        raise ValueError(f"{name} 必須是有限且非負的量測值")
    return n


def sheet(*, good_output, cdd, actual_kwh, electric_submeters, gas_nm3,
          gas_lhv_mj_nm3, expected_intervals, valid_intervals,
          reconciliation_tolerance_kwh="1000"):
    prod = nonnegative(good_output, "良品")
    degree = nonnegative(cdd, "CDD")
    actual = nonnegative(actual_kwh, "用電")
    volume = nonnegative(gas_nm3, "氣體體積")
    lhv = nonnegative(gas_lhv_mj_nm3, "低位熱值")
    if not (type(valid_intervals) is type(expected_intervals) is int and
            expected_intervals > 0 and 0 <= valid_intervals <= expected_intervals):
        raise ValueError("區間筆數無效")
    if not lhv:
        raise ValueError("低位熱值必須大於零")
    tolerance = nonnegative(reconciliation_tolerance_kwh, "電表對帳容差")
    coverage = D(valid_intervals) / D(expected_intervals)
    gas = volume * lhv / D("3.6")
    raw = sum((nonnegative(v, name) for name, v in electric_submeters.items()), D(0))
    adjusted = D(20000) + D(5)*prod + D(80)*degree
    # 合成示例的模型驗證範圍及發布門檻；不是 ISO 指定數值。
    in_domain = D(8000) <= prod <= D(12000) and D(80) <= degree <= D(220)
    residual = actual - raw
    reasons = []
    if not in_domain:
        reasons.append("outside_model_domain")
    if coverage < D(".995"):
        reasons.append("insufficient_interval_coverage")
    # 合成例題：主分表同期間、同邊界，且分表互斥。
    if actual == 0 and raw > 0:
        reasons.append("zero_main_with_positive_submeters")
    elif actual == raw == 0 and prod > 0:
        # 此例生產設備由同邊界主表涵蓋；殘差為零仍不證明讀值可信。
        reasons.append("zero_electricity_with_active_production")
    elif residual < -tolerance:
        reasons.append("submeters_exceed_main_beyond_tolerance")
    eligible = not reasons
    variance = adjusted - actual if eligible else None
    return {"electric_actual_kwh": actual, "gas_lhv_kwh": gas,
            "site_energy_kwh": actual + gas,
            "electric_submeters_kwh": raw, "electric_balance_residual_kwh": residual,
            "absolute_residual_share": abs(residual) / actual if actual else None,
            "good_output": prod, "electric_intensity_kwh_per_unit": actual / prod if prod else None,
            "adjusted_electric_baseline_kwh": adjusted if eligible else None,
            "normalization_status": "synthetic_comparable" if eligible else "not_comparable",
            "comparison_hold_reasons": reasons,
            "reconciliation_tolerance_kwh": tolerance,
            "delta_kwh": variance, "improvement_ratio": variance / adjusted if eligible else None,
            "coverage": coverage}


def example(**overrides):
    record = dict(good_output=10000, cdd=150, actual_kwh=78720,
                  electric_submeters={"製程": 39000, "空壓": 22000, "冷卻": 15000},
                  gas_nm3=2400, gas_lhv_mj_nm3="35.8",
                  expected_intervals=2880, valid_intervals=2872)
    record.update(overrides)
    return sheet(**record)


class Tests(unittest.TestCase):
    def test_nominal(self):
        r=example()
        self.assertEqual((r["adjusted_electric_baseline_kwh"], r["delta_kwh"]),
                         (D(82000), D(3280)))
        self.assertEqual((r["improvement_ratio"],r["electric_balance_residual_kwh"]),
                         (D(".04"), D(2720)))
        self.assertEqual(r["electric_intensity_kwh_per_unit"], D("7.872"))
        self.assertEqual(r["site_energy_kwh"].quantize(D(".01")), D("102586.67"))

    def test_hold_when_missing_or_extrapolated(self):
        for r in (example(valid_intervals=2800), example(good_output=20000)):
            self.assertIsNone(r["improvement_ratio"])
            self.assertEqual(r["normalization_status"],"not_comparable")

    def test_negative_and_wrong_counts_rejected(self):
        for args in ({"gas_lhv_mj_nm3":0},{"actual_kwh":"NaN"},{"valid_intervals":-1}):
            with self.assertRaises(ValueError):
                example(**args)

    def test_conflicting_meters_withhold_comparison(self):
        for actual, residual, reason in (
            (70000, -6000, "submeters_exceed_main_beyond_tolerance"),
            (0, -76000, "zero_main_with_positive_submeters"),
            (74999, -1001, "submeters_exceed_main_beyond_tolerance"),
        ):
            with self.subTest(actual=actual):
                r = example(actual_kwh=actual)
                self.assertEqual(r["electric_actual_kwh"], D(actual))
                self.assertEqual(r["electric_submeters_kwh"], D(76000))
                self.assertEqual(r["electric_balance_residual_kwh"], D(residual))
                self.assertEqual(r["comparison_hold_reasons"], [reason])
                self.assertEqual(r["coverage"], D(2872) / D(2880))
                self.assertEqual(r["normalization_status"], "not_comparable")
                for field in ("adjusted_electric_baseline_kwh", "delta_kwh", "improvement_ratio"):
                    self.assertIsNone(r[field])

    def test_tolerance_boundary(self):
        self.assertEqual(example(actual_kwh=75000)["normalization_status"], "synthetic_comparable")
        with self.assertRaises(ValueError):
            example(reconciliation_tolerance_kwh=-1)

    def test_zero_main_hold_even_with_small_subtotal(self):
        r = example(actual_kwh=0, electric_submeters={"製程": 1}, valid_intervals=2800)
        self.assertEqual(r["comparison_hold_reasons"],
                         ["insufficient_interval_coverage", "zero_main_with_positive_submeters"])
        self.assertIsNone(r["improvement_ratio"])

    def test_zero_electricity_during_production_holds_comparison(self):
        for meters in ({"製程": 0, "空壓": 0, "冷卻": 0}, {}):
            with self.subTest(meters=meters):
                r = example(actual_kwh=0, electric_submeters=meters)
                self.assertEqual(r["good_output"], D(10000))
                self.assertEqual(r["coverage"], D(2872) / D(2880))
                for field in ("electric_actual_kwh", "electric_submeters_kwh",
                              "electric_balance_residual_kwh"):
                    self.assertEqual(r[field], D(0))
                self.assertEqual(r["comparison_hold_reasons"],
                                 ["zero_electricity_with_active_production"])
                self.assertEqual(r["normalization_status"], "not_comparable")
                for field in ("adjusted_electric_baseline_kwh", "delta_kwh",
                              "improvement_ratio", "absolute_residual_share"):
                    self.assertIsNone(r[field])

    def test_zero_denominator(self):
        r=example(good_output=0, actual_kwh=0, electric_submeters={})
        self.assertIsNone(r["electric_intensity_kwh_per_unit"])
        self.assertIsNone(r["absolute_residual_share"])
        self.assertEqual(r["comparison_hold_reasons"], ["outside_model_domain"])


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true")
    p.add_argument("--scenario", choices=("nominal", "mismatch", "zero-main", "zero-all"), default="nominal",
                   help="切換正常、主分表差額過大、僅主表為零或主分表同時為零的教學案例")
    args=p.parse_args()
    if args.test:
        return 0 if unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    # Decimal 以明確十進位字串輸出；消費端依 schema 解析，不偷偷轉二進位 float。
    scenario = {"nominal": {}, "mismatch": {"actual_kwh": 70000},
                "zero-main": {"actual_kwh": 0},
                "zero-all": {"actual_kwh": 0,
                             "electric_submeters": {"製程": 0, "空壓": 0, "冷卻": 0}}}[args.scenario]
    print(json.dumps(example(**scenario), ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
