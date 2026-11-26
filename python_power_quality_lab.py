"""離線電力品質算例：只用 Python 標準庫與合成資料。"""
from cmath import rect
from math import cos, hypot, isfinite, radians
from statistics import fmean
import unittest


def ratio_percent(numerator, denominator):
    if not all(isfinite(v) for v in (numerator, denominator)) or numerator < 0 or denominator <= 0:
        raise ValueError("分子必須非負且分母必須大於零，兩者須為有限數")
    return 100 * numerator / denominator


def harmonic_percent(components, reference):
    """components 只放選定階數的諧波 RMS，不含基波或直流。"""
    components = tuple(components)
    if any(not isfinite(x) or x < 0 for x in components):
        raise ValueError("諧波 RMS 必須是非負有限數")
    return ratio_percent(hypot(*components), reference)


def line_unbalance(va, vb, vc):
    """同步量得的基波相對相量，ABC 相序，由相電壓算 IEC 型 VUF。"""
    if any(not isfinite(abs(v)) for v in (va, vb, vc)):
        raise ValueError("相量必須是有限數")
    a = rect(1, radians(120))
    # 接收 Va/Vb/Vc；線間電壓由相量相減，不能相減 RMS 數字。
    positive = (va + a * vb + a**2 * vc) / 3
    negative = (va + a**2 * vb + a * vc) / 3
    scale = max(abs(va), abs(vb), abs(vc))
    if abs(positive) <= 1e-12 * scale:
        raise ValueError("正序太低；先確認相序和資料品質")
    ll = [abs(va - vb), abs(vb - vc), abs(vc - va)]
    avg = fmean(ll)
    return (ratio_percent(abs(negative), abs(positive)),
            ratio_percent(max(abs(x-avg) for x in ll), avg))


def sag_summary(rms, *, reference, step_seconds, start_pu, end_pu):
    """單相教學事件；步距固定，無時間跳號或缺值。未結束事件拒絕計算。"""
    if not isfinite(step_seconds) or step_seconds <= 0 or not (0 < start_pu < end_pu <= 1):
        raise ValueError("不合法的事件設定")
    events = []
    first = None
    for step, value in enumerate(rms):
        pu = ratio_percent(value, reference) / 100
        if first is None and pu < start_pu:
            first, low = step, pu
        elif first is not None:
            if pu >= end_pu:
                events.append((low, (step - first) * step_seconds))
                first = None
            else:
                low = min(low, pu)
    if first is not None:
        raise ValueError("事件尚未結束／資料截斷")
    return events


def example():
    ih, i1, il = (12, 9), 40, 60
    dpf = cos(radians(30))
    pf = i1 * dpf / hypot(i1, *ih)  # V 只有基波；不是一般畸變公式。
    unbalance = line_unbalance(230, rect(218, radians(-120)), rect(236, radians(120)))
    sag, = sag_summary([230, 180, 179, 193, 212], reference=230,
                       step_seconds=1/120, start_pu=.90, end_pu=.92)
    return dpf, pf, harmonic_percent(ih, i1), harmonic_percent(ih, il), *unbalance, *sag


class PowerQualityTests(unittest.TestCase):
    def test_worked_example(self):
        dpf, pf, thd, tdd, iec, nema, residual, duration = example()
        for actual, want in zip((dpf, pf, thd, tdd, iec, nema, residual, duration),
                                (.8660254, .8108849, 37.5, 25, 2.32083, 2.18196, 179/230, .025)):
            self.assertAlmostEqual(actual, want, places=4)

    def test_balanced(self):
        for v in line_unbalance(230, rect(230, radians(-120)), rect(230, radians(120))):
            self.assertAlmostEqual(v, 0)

    def test_invalid_and_unknown(self):
        with self.assertRaises(ValueError):
            harmonic_percent([3, 4], 0)
        with self.assertRaises(ValueError):
            harmonic_percent([float("nan")], 100)
        with self.assertRaises(ValueError):
            line_unbalance(0, 0, 0)
        with self.assertRaises(ValueError):
            sag_summary([230, 180], reference=230, step_seconds=1/120, start_pu=.9, end_pu=.92)

    def test_hysteresis(self):
        self.assertEqual(sag_summary([90, 89, 90, 91, 92], reference=100,
                                     step_seconds=1, start_pu=.9, end_pu=.92), [(.89, 3)])


if __name__ == "__main__":
    dpf, pf, thd, tdd, iec, nema, residual, duration = example()
    print(f"DPF={dpf:.4f}, PF={pf:.4f}; THDi={thd:.2f}%, TDD={tdd:.2f}%")
    print(f"VUF={iec:.3f}%, NEMA={nema:.3f}%; sag={residual:.4f} pu / {duration*1000:.1f} ms")
