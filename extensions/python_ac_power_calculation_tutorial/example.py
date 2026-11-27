"""三相電壓不平衡率、各相功率加總與功率因數改善電容量估算（標準函式庫 cmath）。"""
import cmath
import math

# 某配電盤三相量測（相電壓、相電流有效值，電流落後電壓的角度）
PHASES = {
    "R": dict(v=228.0, i=182.0, lag_deg=36.0),
    "S": dict(v=224.5, i=176.0, lag_deg=38.5),
    "T": dict(v=231.2, i=169.0, lag_deg=34.0),
}
LINE_V = {"RS": 392.4, "ST": 394.1, "TR": 398.9}


def unbalance_pct(values):
    """NEMA MG-1 定義：最大偏差 ÷ 平均 × 100%。"""
    avg = sum(values) / len(values)
    return max(abs(v - avg) for v in values) / avg * 100


def phase_power(v, i, lag_deg):
    s = v * i * cmath.exp(1j * math.radians(lag_deg)) / 1000     # 複功率 kVA，落後為正 Q
    return s


def capacitor_kvar(p_kw, pf_now, pf_target):
    return p_kw * (math.tan(math.acos(pf_now)) - math.tan(math.acos(pf_target)))


if __name__ == "__main__":
    total = 0j
    for name, ph in PHASES.items():
        s = phase_power(**ph)
        total += s
        print(f"{name} 相：P={s.real:6.2f} kW  Q={s.imag:6.2f} kvar  S={abs(s):6.2f} kVA  PF={s.real / abs(s):.3f}")
    print(f"合計：P={total.real:.2f} kW  Q={total.imag:.2f} kvar  S={abs(total):.2f} kVA")
    pf = total.real / abs(total)
    naive_s = sum(abs(phase_power(**ph)) for ph in PHASES.values())
    print(f"三相功率因數 = ΣP ÷ |ΣS| = {pf:.3f}（若把各相 kVA 直接相加得 {naive_s:.2f} kVA）")
    vu = unbalance_pct(list(LINE_V.values()))
    iu = unbalance_pct([ph["i"] for ph in PHASES.values()])
    print(f"線電壓不平衡 {vu:.2f}%，電流不平衡 {iu:.2f}%")
    for target in (0.90, 0.95, 0.98):
        kvar = capacitor_kvar(total.real, pf, target)
        print(f"由 PF {pf:.3f} 改善到 {target:.2f}：約需 {kvar:.1f} kvar 電容")
