"""NumPy 向量化：一次計算 24 小時 × 6 台冰機的冷量、kW/RT，並用遮罩排除無效資料（需 numpy）。"""
import numpy as np

rng = np.random.default_rng(42)                 # 固定種子，輸出可重現
hours, chillers = 24, 6
flow = rng.uniform(30, 50, (hours, chillers))                 # L/s
t_ret = rng.uniform(11.5, 13.0, (hours, chillers))
t_sup = rng.uniform(6.8, 7.2, (hours, chillers))
kw = rng.uniform(120, 190, (hours, chillers))
kw[3:5, 2] = 0.0                               # 第 3 台在 03:00–05:00 停機
t_ret[10, 4] = np.nan                          # 感測器缺值

if __name__ == "__main__":
    print("numpy", np.__version__.split(".")[0] + ".x")
    rt = flow * 4.186 * (t_ret - t_sup) / 3.517              # 廣播運算：整個 24×6 陣列一次算完
    valid = (kw > 5) & np.isfinite(rt) & (t_ret - t_sup > 1.0)
    kw_per_rt = np.where(valid, kw / np.where(rt > 0, rt, np.nan), np.nan)
    print("無效筆數：", int((~valid).sum()), "（停機 2 筆 + 缺值 1 筆）")
    daily = np.nansum(np.where(valid, kw, 0), axis=0) / np.nansum(np.where(valid, rt, 0), axis=0)
    for i, v in enumerate(daily, 1):
        print(f"冰機 {i}：日平均 {v:.3f} kW/RT")
    best = int(np.nanargmin(daily)) + 1
    print(f"最有效率：冰機 {best}；全廠加權 {np.nansum(kw[valid]) / np.nansum(rt[valid]):.3f} kW/RT")
    print(f"錯誤示範：直接平均每小時 kW/RT = {np.nanmean(kw_per_rt):.3f}（未以冷量加權）")
