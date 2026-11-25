"""理想正弦、供電側正向合成算例；不接電表、不操作電力設備。"""
from dataclasses import dataclass
import math
import unittest


@dataclass(frozen=True)
class Power:
    p_kw: float
    q_kvar: float

    @property
    def s_kva(self):
        return math.hypot(self.p_kw, self.q_kvar)

    @property
    def pf(self):
        return self.p_kw / self.s_kva if self.s_kva else None

    @property
    def phi_deg(self):
        return math.degrees(math.atan2(self.q_kvar, self.p_kw)) if self.s_kva else None


def sinusoidal(volts_rms, amps_rms, phi_deg, *, balanced_3ph=False):
    values = (volts_rms, amps_rms, phi_deg)
    if not all(math.isfinite(x) for x in values):
        raise ValueError("只能接受有限數值")
    if min(volts_rms, amps_rms) < 0 or not -90 <= phi_deg <= 90:
        raise ValueError("RMS 不可為負；本例僅涵蓋吸收有功的負載")
    # 三相的 volts 是線對線、amps 是線電流；phi 是相電壓/相電流角。
    s = (math.sqrt(3) if balanced_3ph else 1) * volts_rms * amps_rms / 1000
    phi = math.radians(phi_deg)
    # 消除 cos(±90°) 的微小浮點殘留。
    return Power(0.0 if abs(phi_deg) == 90 else s * math.cos(phi),
                 s * math.sin(phi))


def aggregate(loads):
    """同一時間窗與邊界；此例限可用單一複功率表示的正弦系統。"""
    loads = tuple(loads)
    if any(not (math.isfinite(x.p_kw) and math.isfinite(x.q_kvar))
           for x in loads):
        raise ValueError("P、Q 必須為有限值")
    return Power(math.fsum(x.p_kw for x in loads), math.fsum(x.q_kvar for x in loads))


def true_pf_1ph(p_kw, volts_rms, amps_rms):
    """P 已由同窗平均 v(t)*i(t) 取得；V、I 為總 RMS。"""
    if not all(math.isfinite(x) for x in (p_kw, volts_rms, amps_rms)):
        raise ValueError("只能接受有限數值")
    if min(volts_rms, amps_rms) < 0:
        raise ValueError("RMS 不可為負")
    s = volts_rms * amps_rms / 1000
    if abs(p_kw) > s and not math.isclose(abs(p_kw), s, rel_tol=1e-12):
        raise ValueError("|P| 不可大於 S，請核對時間窗和量測定義")
    return max(-1, min(1, p_kw / s)) if s else None


def example():
    a = sinusoidal(400, 100, math.degrees(math.acos(.8)), balanced_3ph=True)
    b = sinusoidal(400, 60, -30, balanced_3ph=True)
    return a, b, aggregate((a, b))


class Tests(unittest.TestCase):
    def test_balanced_and_sum(self):
        a, b, total = example()
        self.assertAlmostEqual(a.s_kva, 69.2820323028)
        self.assertAlmostEqual(a.pf, .8)
        self.assertGreater(a.q_kvar, 0)
        self.assertLess(b.phi_deg, 0)
        self.assertAlmostEqual(total.q_kvar, 20.7846096908)
        self.assertLess(total.s_kva, a.s_kva + b.s_kva)

    def test_single_phase_and_bad_input(self):
        self.assertAlmostEqual(sinusoidal(230, 10, 0).p_kw, 2.3)
        self.assertIsNone(sinusoidal(230, 0, 0).phi_deg)
        for v, i, phi in ((-1, 10, 10), (230, 10, 110), (math.nan, 10, 0)):
            with self.assertRaises(ValueError):
                sinusoidal(v, i, phi)

    def test_harmonic_pf_and_limit(self):
        self.assertAlmostEqual(true_pf_1ph(1.84, 230, 10), .8)
        self.assertIsNone(true_pf_1ph(0, 230, 0))
        with self.assertRaises(ValueError):
            true_pf_1ph(2.31, 230, 10)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        unittest.main(argv=["lab"])
    else:
        for label, x in zip(("A 感性", "B 容性", "合計"), example()):
            print(f"{label}: P={x.p_kw:.3f} kW, Q={x.q_kvar:+.3f} kvar, "
                  f"S={x.s_kva:.3f} kVA, PF={x.pf:.4f}, φ={x.phi_deg:+.2f}°")
        print("單相示意真實 PF:", true_pf_1ph(1.84, 230, 10))
