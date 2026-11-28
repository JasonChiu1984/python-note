"""由狀態事件紀錄計算稼動率與 OEE，並把「未知」時段獨立列出（標準函式庫）。"""
from datetime import datetime, timedelta

PLANNED = (datetime(2026, 11, 20, 8, 0), datetime(2026, 11, 20, 16, 0))   # 計畫生產 8 小時
EVENTS = [                     # (開始時間, 狀態)；狀態持續到下一筆事件
    ("08:00", "run"), ("09:40", "stop_changeover"), ("10:10", "run"),
    ("12:00", "unknown"),      # 閘道器斷線，無回授
    ("12:20", "run"), ("14:05", "stop_fault"), ("14:50", "run"),
]
IDEAL_CYCLE_S = 30            # 理想節拍：每件 30 秒
GOOD, TOTAL = 690, 720        # 由獨立計數器確認涵蓋整個計畫窗的良品與總產出


def durations():
    day = PLANNED[0].date()
    times = [datetime.combine(day, datetime.strptime(t, "%H:%M").time()) for t, _ in EVENTS]
    times.append(PLANNED[1])
    acc: dict[str, timedelta] = {}
    for (start, end), (_, state) in zip(zip(times, times[1:]), EVENTS):
        acc[state] = acc.get(state, timedelta()) + (end - start)
    return acc


def full_window_oee(planned_seconds, good, ideal_cycle_s, *, counts_cover_window):
    """只用同一計畫窗內、覆蓋已核實的良品數；無法核實則不報。"""
    if planned_seconds <= 0 or ideal_cycle_s <= 0 or good < 0:
        raise ValueError("計畫秒數與理想節拍須為正，良品數不得為負")
    if not counts_cover_window:
        return None
    return good * ideal_cycle_s / planned_seconds


if __name__ == "__main__":
    acc = durations()
    planned = PLANNED[1] - PLANNED[0]
    for state, d in sorted(acc.items()):
        print(f"{state:<17} {d}")
    unknown = acc.get("unknown", timedelta())
    run = acc.get("run", timedelta())
    known = planned - unknown
    print(f"未知時段 {unknown}；狀態涵蓋率 {known / planned:.1%}")
    if known:
        print(f"已知時段的運轉占比 = {run} ÷ {known} = {run / known:.1%}")
    else:
        print("已知時段的運轉占比：無法計算")
    print(f"全窗可用率範圍：{run / planned:.1%}～{(run + unknown) / planned:.1%}")
    print(f"全窗品質 Q = {GOOD} ÷ {TOTAL} = {GOOD / TOTAL:.1%}")
    oee = full_window_oee(planned.total_seconds(), GOOD, IDEAL_CYCLE_S,
                          counts_cover_window=True)  # 本合成案例的前提，不是由回授推得
    print(f"全窗 OEE = {GOOD} × {IDEAL_CYCLE_S}s ÷ {planned.total_seconds():.0f}s = {oee:.1%}")
    print("有未知運轉時間，不混用全窗件數與已知運轉時間估算效能 P。")
