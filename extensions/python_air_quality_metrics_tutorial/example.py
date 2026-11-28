"""CO2 八小時移動平均、資料涵蓋率與外氣量估算（教學模型）。

- 室內空氣品質標準：CO2 八小時值 1,000 ppm、PM2.5 二十四小時值 35 μg/m3。
- 本例規定一個八小時窗至少要有 75% 的分鐘資料才計算平均，這是設計選擇，不是法規。
- 單一感測器的移動平均只與監測參考值比較，不能代替公告場所的法定採樣與符合性判定。
- 外氣量以穩態質量平衡估算：Q = N × G ÷ (Cin − Cout)，G 取成人坐姿約 0.005 L/s/人的近似值。
"""
from datetime import datetime, timedelta
from statistics import fmean

LIMIT_CO2_8H = 1000
MIN_COVERAGE = 0.75
CO2_GEN_LPS = 0.005          # L/s/人，近似值


def synthetic_day(start):
    """08:00–18:00 的會議室，每分鐘一筆；12:00–12:40 通訊中斷造成缺值。"""
    rows = []
    co2 = 450.0
    for m in range(600):
        t = start + timedelta(minutes=m)
        people = 0 if t.hour < 9 or t.hour >= 17 else (12 if 13 <= t.hour < 16 else 6)
        target = 430 + people * 75                      # 簡化的穩態濃度
        co2 += (target - co2) * 0.05                    # 一階逼近
        if not (t.hour == 12 and t.minute < 40):
            rows.append((t, round(co2)))
    return rows


def rolling_8h(rows, end):
    window_start = end - timedelta(hours=8)
    values = [v for t, v in rows if window_start < t <= end]
    coverage = len(values) / 480
    if coverage < MIN_COVERAGE:
        return None, coverage
    return fmean(values), coverage


def outdoor_air_lps(people, c_in, c_out=420):
    """穩態估算所需外氣量 L/s；c_in 必須高於 c_out。"""
    if c_in <= c_out:
        raise ValueError("室內濃度需高於室外，才能用 CO2 估算外氣量")
    return people * CO2_GEN_LPS / ((c_in - c_out) * 1e-6)


if __name__ == "__main__":
    rows = synthetic_day(datetime(2026, 11, 20, 8, 0))
    print(f"取樣筆數：{len(rows)}（應有 600 筆，缺 {600 - len(rows)} 筆）")
    peak_t, peak_v = max(rows, key=lambda r: r[1])
    print(f"單筆最高：{peak_v} ppm @ {peak_t:%H:%M}")
    for hh in (16, 17, 18):
        end = datetime(2026, 11, 20, hh, 0) - timedelta(minutes=1) if hh == 18 else datetime(2026, 11, 20, hh, 0)
        avg, cov = rolling_8h(rows, end)
        if avg is None:
            verdict = "資料不足"
        else:
            relation = "高於" if avg > LIMIT_CO2_8H else "未高於"
            verdict = f"{relation} {LIMIT_CO2_8H:,} ppm 監測參考值"
        shown = "—" if avg is None else f"{avg:.0f} ppm"
        print(f"截至 {end:%H:%M} 的八小時平均：{shown}，涵蓋率 {cov:.0%}，{verdict}")
    for people in (6, 12):
        q = outdoor_air_lps(people, c_in=1000)
        print(f"{people} 人、維持室內 1,000 ppm 所需外氣量：約 {q:.0f} L/s（{q * 3.6:.0f} m3/h）")
