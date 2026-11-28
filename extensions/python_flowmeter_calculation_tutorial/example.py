"""流量計訊號換算：4–20 mA（線性與差壓開方）、小流量切除、脈衝累計器溢位處理（標準函式庫）。"""
import math


def check_ma(ma):
    """NAMUR NE43：3.8–20.5 mA 為量測範圍；≤3.6 或 ≥21 mA 為故障訊號；其間為超出量測範圍。"""
    if ma <= 3.6 or ma >= 21.0:
        raise ValueError(f"{ma} mA 為故障訊號（斷線、短路或變送器自診斷告警）")
    if ma < 3.8 or ma > 20.5:
        raise ValueError(f"{ma} mA 超出量測範圍（飽和），數值不可信")


def ma_to_flow_linear(ma, span):
    check_ma(ma)
    pct = max(0.0, (ma - 4) / 16)
    return pct * span


def ma_to_flow_dp(ma, span, cutoff_pct=0.05):
    """差壓式未線性化：流量 ∝ √差壓。低於切除點直接歸零，避免零點雜訊被開方放大。"""
    check_ma(ma)
    dp_pct = max(0.0, (ma - 4) / 16)
    flow_pct = math.sqrt(dp_pct)
    return 0.0 if flow_pct < cutoff_pct else flow_pct * span


def pulse_delta(prev, curr, rollover=65_536):
    """16 位元脈衝計數器（例如 Modbus 單一暫存器）跨越 65535 → 0 時的增量。"""
    if curr >= prev:
        return curr - prev
    return curr + rollover - prev


if __name__ == "__main__":
    span = 100.0                                   # m3/h
    print(" mA    線性 m3/h   差壓開方 m3/h")
    for ma in (4.0, 4.04, 4.16, 8.0, 12.0, 20.0):
        print(f"{ma:5.2f} {ma_to_flow_linear(ma, span):9.2f} {ma_to_flow_dp(ma, span):12.2f}")
    for bad in (2.1, 20.8):
        try:
            ma_to_flow_linear(bad, span)
        except ValueError as e:
            print(f"{bad} mA：", e)

    k_factor = 10.0                                # 脈衝／m3
    readings = [65_210, 65_480, 65_530, 120, 410]  # 每 5 分鐘讀一次，第 4 筆溢位
    total = 0
    for a, b in zip(readings, readings[1:]):
        d = pulse_delta(a, b)
        total += d
        print(f"{a:>6} → {b:>6}：+{d:>4} 脈衝 = {d / k_factor:5.1f} m3")
    print(f"20 分鐘累計 {total} 脈衝 = {total / k_factor:.1f} m3，平均 {total / k_factor * 3:.1f} m3/h")
