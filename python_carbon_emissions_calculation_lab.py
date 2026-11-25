"""離線合成工廠溫室氣體教具；係數均為假設，不能用於申報。Python 3.9+。"""
import argparse
import json
import unittest
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

D = Decimal
FACTORS = {
    "diesel": ("2.70", "kgCO2e/L", "TRAIN-DIESEL", "教學燃料綜合係數"),
    "refrigerant": ("1000", "kgCO2e/kg", "TRAIN-GWP", "假想單一冷媒的 GWP100"),
    "grid": ("0.45", "kgCO2e/kWh", "TRAIN-GRID", "假想電網平均"),
    "contract": ("0.05", "kgCO2e/kWh", "TRAIN-CONTRACT", "假想合格契約"),
    "residual": ("0.55", "kgCO2e/kWh", "TRAIN-RESIDUAL", "假想剩餘組合"),
}


def amount(value, label):
    """先驗證再乘；空白、缺值、負數、NaN 和 Infinity 都不是 0。"""
    try:
        n = D(str(value))
    except (TypeError, ValueError, InvalidOperation) as error:
        raise ValueError(f"{label}：需要明確數值") from error
    if not n.is_finite() or not D(0) <= n <= D("1000000000"):
        raise ValueError(f"{label}：需為 0 至十億的有限數")
    return n


def calculate(diesel_l, leaked_kg, electricity_kwh, contracted_kwh=None):
    """輸入的冷媒量須是逸散量；合格契約量未驗證時傳 None，非傳 0。"""
    diesel_l = amount(diesel_l, "柴油 L")
    leaked_kg = amount(leaked_kg, "冷媒 kg")
    electricity_kwh = amount(electricity_kwh, "外購電力 kWh")
    contract = None if contracted_kwh is None else amount(contracted_kwh, "合格契約 kWh")
    if contract is not None and contract > electricity_kwh:
        raise ValueError("合格契約電量不可超過同站同期間外購電量")
    fuel = diesel_l * D(FACTORS["diesel"][0])
    refrigerant = leaked_kg * D(FACTORS["refrigerant"][0])
    scope1 = fuel + refrigerant
    location = electricity_kwh * D(FACTORS["grid"][0])
    residual = None if contract is None else electricity_kwh - contract
    covered_emissions = None if contract is None else contract * D(FACTORS["contract"][0])
    residual_emissions = None if residual is None else residual * D(FACTORS["residual"][0])
    market = None if covered_emissions is None else covered_emissions + residual_emissions
    return {
        "synthetic": True, "unit": "kgCO2e",
        "fuel": fuel, "refrigerant": refrigerant, "scope1": scope1,
        "scope2_location": location, "scope2_market": market,
        "scope2_market_status": "pending_evidence" if market is None else "synthetic_example",
        "contract_emissions": covered_emissions, "residual_emissions": residual_emissions,
        "total_location": scope1 + location,
        "total_market": None if market is None else scope1 + market,
        "factors": {
            k: {"value": v[0], "unit": v[1], "id": v[2], "source": v[3],
                "reference_year": 2025, "region": "DEMO", "version": 1}
            for k, v in FACTORS.items()
        },
    }


def as_json(report):
    """對外報表用字串保存十進位精度；只在輸出四捨五入至兩位。"""
    def encode(value):
        if isinstance(value, Decimal):
            return str(value.quantize(D("0.01"), rounding=ROUND_HALF_UP))
        raise TypeError(type(value).__name__)
    return json.dumps(report, default=encode, ensure_ascii=False, indent=2)


class ContractTests(unittest.TestCase):
    def test_demo(self):
        r = calculate(800, "2.5", 120000, 40000)
        self.assertEqual(r["scope1"], 4660)
        self.assertEqual(r["scope2_location"], 54000)
        self.assertEqual(r["scope2_market"], 46000)
        self.assertEqual(r["total_location"], 58660)
        self.assertEqual(r["total_market"], 50660)

    def test_unknown_market(self):
        r = calculate(800, "2.5", 120000)
        self.assertIsNone(r["scope2_market"])
        self.assertIsNone(r["total_market"])
        self.assertEqual(r["scope2_market_status"], "pending_evidence")

    def test_zero_verified_contract(self):
        self.assertEqual(calculate(0, 0, 100, 0)["scope2_market"], 55)

    def test_reject_invalid_measurements(self):
        for x in ("", None, -1, "NaN", "Infinity"):
            with self.subTest(x=x), self.assertRaises(ValueError):
                calculate(x, 0, 0)

    def test_reject_double_allocating_kwh(self):
        with self.assertRaises(ValueError):
            calculate(0, 0, 100, 101)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="假想合格契約覆蓋 40,000 kWh")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--diesel-l", default="800")
    parser.add_argument("--leaked-kg", default="2.5")
    parser.add_argument("--electricity-kwh", default="120000")
    parser.add_argument("--contracted-kwh", help="僅填已查證數量；缺少證據時不指定")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=["lab"])
    else:
        try:
            r = (calculate(800, "2.5", 120000, 40000) if args.demo else
                 calculate(args.diesel_l, args.leaked_kg,
                           args.electricity_kwh, args.contracted_kwh))
            print(as_json(r))
        except ValueError as error:
            parser.error(str(error))
