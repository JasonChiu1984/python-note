"""變頻泵浦：泵曲線 × 系統曲線求運轉點，並比較有／無靜揚程時的節能估算（標準函式庫）。

泵曲線（額定轉速）：H = 42 − 0.0012 Q²     （Q：m3/h，H：m）
系統曲線：H = H_static + k Q²
轉速比 n 時泵曲線依相似定律：H = 42 n² − 0.0012 Q²
"""
import math

A, B = 42.0, 0.0012           # 泵曲線係數
ETA = 0.72                    # 泵＋馬達＋變頻器總效率（簡化為定值）
RHO_G = 1000 * 9.81


def operating_point(n, h_static, k):
    """解 A n² − B Q² = h_static + k Q²。"""
    q2 = (A * n * n - h_static) / (B + k)
    if q2 <= 0:
        return 0.0, h_static          # 轉速太低，無法克服靜揚程
    q = math.sqrt(q2)
    return q, h_static + k * q2


def electric_kw(q_m3h, h_m):
    return RHO_G * (q_m3h / 3600) * h_m / ETA / 1000


def speed_for_flow(target_q, h_static, k):
    lo, hi = 0.2, 1.0
    for _ in range(60):               # 二分法
        mid = (lo + hi) / 2
        q, _ = operating_point(mid, h_static, k)
        lo, hi = (mid, hi) if q < target_q else (lo, mid)
    return hi


if __name__ == "__main__":
    for label, h_static in (("閉式冰水迴路（無靜揚程）", 0.0), ("冷卻水塔開式迴路（靜揚程 8 m）", 8.0)):
        k = (30.0 - h_static) / 150.0 ** 2          # 讓 150 m3/h 時系統需 30 m
        q100, h100 = operating_point(1.0, h_static, k)
        p100 = electric_kw(q100, h100)
        print(f"== {label}")
        print(f"  額定轉速運轉點：Q={q100:.1f} m3/h，H={h100:.1f} m，電力 {p100:.1f} kW")
        for frac in (0.8, 0.6):
            target = q100 * frac
            n = speed_for_flow(target, h_static, k)
            q, h = operating_point(n, h_static, k)
            p = electric_kw(q, h)
            print(f"  流量 {frac:.0%}：轉速 {n:.1%}，H={h:.1f} m，電力 {p:.1f} kW"
                  f"（立方定律估 {p100 * frac ** 3:.1f} kW）")
