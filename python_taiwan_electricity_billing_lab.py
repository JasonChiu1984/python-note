"""Python 3.10+：住宅流動電費與機房假設式 TOU 小計；並非帳單引擎。"""
import argparse
import json
import unittest
from decimal import Decimal, InvalidOperation

D = Decimal
BANDS = (120, 330, 500, 700, 1000)
RATES = {
    "summer": ("1.78", "2.55", "3.80", "5.14", "6.44", "8.86"),
    "other": ("1.78", "2.26", "3.13", "4.24", "5.27", "7.03"),
}
DEMO = {
    "peak": ("10000", "6.00"),
    "shoulder": ("18000", "4.00"),
    "off_peak": ("32000", "2.50"),
}


def nonnegative(value):
    try:
        result = D(str(value))
    except InvalidOperation as exc:
        raise ValueError("必須是十進位數值") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("數值必須有限且非負")
    return result


def residential(kwh, season, cycles):
    if cycles not in (1, 2) or season not in RATES:
        raise ValueError("僅支援單一季節，且級距為 1 或 2 個月")
    kwh = nonnegative(kwh)
    previous = D(0)
    lines = []
    for limit, rate in zip((*BANDS, None), RATES[season]):
        upper = kwh if limit is None else min(kwh, D(limit) * cycles)
        quantity = max(D(0), upper - previous)
        if quantity:
            lines.append(dict(kwh=quantity, nt_per_kwh=D(rate),
                              subtotal=quantity * D(rate)))
        if upper >= kwh:
            break
        previous = upper
    return dict(scope="住宅表燈非時間流動電費；不含底度費與其他調整",
                table_effective="2025-10-01", checked="2026-11-25",
                season=season, months=cycles, kwh=kwh, lines=lines,
                energy_subtotal=sum((line["subtotal"] for line in lines), D(0)))


def tou(buckets, contracted_kw, contract_rate, max_kw):
    if set(buckets) != set(DEMO):
        raise ValueError("需齊備 peak、shoulder 與 off_peak 三組合計用電")
    detail = {}
    for name, (energy, rate) in buckets.items():
        kwh, nt_per_kwh = nonnegative(energy), nonnegative(rate)
        detail[name] = dict(kwh=kwh, nt_per_kwh=nt_per_kwh,
                            subtotal=kwh * nt_per_kwh)
    contracted_kw, contract_rate, max_kw = map(
        nonnegative, (contracted_kw, contract_rate, max_kw))
    energy = sum(line["subtotal"] for line in detail.values())
    basic = contracted_kw * contract_rate
    return dict(scope="假設模型；1 計費月、單一契約；不含超約加收及其他調整",
                buckets=detail, energy_subtotal=energy, basic_subtotal=basic,
                modeled_subtotal=energy + basic, contracted_kw=contracted_kw,
                modeled_contract_rate=contract_rate, measured_max_kw=max_kw,
                excess_flag_kw=max(D(0), max_kw - contracted_kw))


class TestBilling(unittest.TestCase):
    def test_november(self):
        self.assertEqual(residential("400", "other", 1)["energy_subtotal"], D("907.30"))

    def test_summer(self):
        self.assertEqual(residential("400", "summer", 1)["energy_subtotal"], D("1015.10"))

    def test_two_months(self):
        self.assertEqual(residential("800", "other", 2)["energy_subtotal"], D("1814.60"))

    def test_open_tier(self):
        self.assertEqual(residential("1001", "other", 1)["lines"][-1]["subtotal"], D("7.03"))

    def test_zero(self):
        self.assertEqual(residential("0", "other", 1)["energy_subtotal"], D(0))

    def test_invalid(self):
        for bad in ("-1", "NaN", "Infinity", "abc"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                residential(bad, "other", 1)
        with self.assertRaises(ValueError):
            residential(300, "mixed", 2)

    def test_tou(self):
        result = tou(DEMO, 180, 150, 200)
        self.assertEqual(result["modeled_subtotal"], D(239000))
        self.assertEqual(result["excess_flag_kw"], D(20))
        self.assertEqual(tou(DEMO, 200, 150, 180)["excess_flag_kw"], D(0))

    def test_tou_missing(self):
        with self.assertRaises(ValueError):
            tou({"peak": ("1", "2")}, 180, 150, 200)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    home = modes.add_parser("residential", help="同季表燈非時間住宅")
    home.add_argument("--kwh", required=True)
    home.add_argument("--season", choices=RATES, required=True)
    home.add_argument("--months", type=int, choices=(1, 2), required=True)
    machine = modes.add_parser("tou-demo", help="已完成時段分桶的假設式算例")
    for key, defaults in DEMO.items():
        machine.add_argument("--" + key.replace("_", "-"), nargs=2, default=defaults,
                             metavar=("KWH", "NT_PER_KWH"))
    machine.add_argument("--contracted-kw", default="180")
    machine.add_argument("--contract-rate", default="150")
    machine.add_argument("--max-kw", default="200")
    modes.add_parser("self-test", help="跑 stdlib unittest")
    args = parser.parse_args()
    if args.mode == "self-test":
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestBilling)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    try:
        if args.mode == "residential":
            result = residential(args.kwh, args.season, args.months)
        else:
            result = tou({name: getattr(args, name) for name in DEMO},
                         args.contracted_kw, args.contract_rate, args.max_kw)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2,
                     default=lambda value: format(value, "f")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
