"""冰機 kW/RT、COP 與全廠能效；並示範低 ΔT 對泵浦用電的影響（標準函式庫）。

冷量 kW = 流量(L/s) × 4.186 × ΔT(°C)；1 RT = 3.517 kW。
"""
RT_KW = 3.517
CP = 4.186                                      # kJ/(kg·K)，以 1 kg/L 近似


def cooling_kw(flow_lps, t_return, t_supply):
    return flow_lps * CP * (t_return - t_supply)


if __name__ == "__main__":
    # 15 分鐘平均資料：冰水 45 L/s、回水 12.5 °C、供水 7.0 °C
    q = cooling_kw(45.0, 12.5, 7.0)
    rt = q / RT_KW
    chiller_kw, chw_pump, cw_pump, tower = 168.0, 18.5, 22.0, 11.0
    plant_kw = chiller_kw + chw_pump + cw_pump + tower
    print(f"冷量 {q:.1f} kW = {rt:.1f} RT")
    print(f"冰機 {chiller_kw} kW → {chiller_kw / rt:.3f} kW/RT，COP {q / chiller_kw:.2f}")
    print(f"全廠 {plant_kw} kW → {plant_kw / rt:.3f} kW/RT，COP {q / plant_kw:.2f}")
    print()
    print("同樣冷量下，ΔT 對冰水流量與泵浦用電的影響（泵浦功率 ∝ 流量³ 的上限估計）：")
    for dt in (5.5, 4.5, 3.5):
        flow = q / (CP * dt)
        pump = chw_pump * (flow / 45.0) ** 3
        print(f"  ΔT {dt} °C → 流量 {flow:5.1f} L/s，冰水泵約 {pump:5.1f} kW，"
              f"全廠 {(chiller_kw + pump + cw_pump + tower) / rt:.3f} kW/RT")
    print()
    print("溫度感測器誤差的影響：供回水各偏 0.2 °C（方向相反）時")
    for err in (0.0, 0.2, -0.2):
        q_err = cooling_kw(45.0, 12.5 + err, 7.0 - err)
        print(f"  誤差 {err:+.1f} °C：冷量 {q_err / RT_KW:6.1f} RT，冰機 {chiller_kw / (q_err / RT_KW):.3f} kW/RT")
