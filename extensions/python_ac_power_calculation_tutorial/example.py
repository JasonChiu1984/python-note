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


def capacitor_kvar(p1_kw, q1_kvar, target_dpf):
    """新增電容的基波估算：p1 > 0，q1 帶號（感性正、容性負）。"""
    if not math.isfinite(p1_kw) or p1_kw <= 0 or not math.isfinite(q1_kvar):
        raise ValueError("基波 kW 須為正值，且 kW、kvar 須為有限數")
    if not 0 < target_dpf <= 1:
        raise ValueError("目標落後位移功率因數須在 (0, 1] 內")
    q1_target = p1_kw * math.tan(math.acos(target_dpf))
    return max(0.0, q1_kvar - q1_target)  # 已超前或已達標：不得再加入電容


if __name__ == "__main__":
    total = 0j
    for name, ph in PHASES.items():
        s = phase_power(**ph)
        total += s
        print(f"{name} 相：P={s.real:6.2f} kW  Q={s.imag:6.2f} kvar  S={abs(s):6.2f} kVA  PF={s.real / abs(s):.3f}")
    print(f"合計：P={total.real:.2f} kW  Q={total.imag:.2f} kvar  S={abs(total):.2f} kVA")
    pf = total.real / abs(total)
    naive_s = sum(abs(phase_power(**ph)) for ph in PHASES.values())
    print(f"本基波模型的向量功率比 = ΣP₁ ÷ |ΣS₁| = {pf:.3f}（若把各相 kVA 直接相加得 {naive_s:.2f} kVA）")
    vu = unbalance_pct(list(LINE_V.values()))
    iu = unbalance_pct([ph["i"] for ph in PHASES.values()])
    print(f"線電壓不平衡 {vu:.2f}%，電流不平衡 {iu:.2f}%")
    for target in (0.90, 0.95, 0.98):
        kvar = capacitor_kvar(total.real, total.imag, target)
        print(f"落後基波目標 {target:.2f}：模擬估算 {kvar:.1f} kvar（非電容組選型）")
