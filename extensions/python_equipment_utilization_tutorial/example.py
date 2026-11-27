"""由狀態事件紀錄計算稼動率與 OEE，並把「未知」時段獨立列出（標準函式庫）。"""
from datetime import datetime, timedelta

PLANNED = (datetime(2026, 11, 20, 8, 0), datetime(2026, 11, 20, 16, 0))   # 計畫生產 8 小時
EVENTS = [                     # (開始時間, 狀態)；狀態持續到下一筆事件
    ("08:00", "run"), ("09:40", "stop_changeover"), ("10:10", "run"),
    ("12:00", "unknown"),      # 閘道器斷線，無回授
    ("12:20", "run"), ("14:05", "stop_fault"), ("14:50", "run"),
]
IDEAL_CYCLE_S = 30            # 理想節拍：每件 30 秒
GOOD, TOTAL = 690, 720        # 良品數、總產出


def durations():
    day = PLANNED[0].date()
    times = [datetime.combine(day, datetime.strptime(t, "%H:%M").time()) for t, _ in EVENTS]
    times.append(PLANNED[1])
    acc: dict[str, timedelta] = {}
    for (start, end), (_, state) in zip(zip(times, times[1:]), EVENTS):
        acc[state] = acc.get(state, timedelta()) + (end - start)
    return acc


if __name__ == "__main__":
    acc = durations()
    planned = PLANNED[1] - PLANNED[0]
    for state, d in sorted(acc.items()):
        print(f"{state:<17} {d}")
    unknown = acc.get("unknown", timedelta())
    run = acc.get("run", timedelta())
    known = planned - unknown
    availability = run / known
    performance = TOTAL * IDEAL_CYCLE_S / run.total_seconds()
    quality = GOOD / TOTAL
    print(f"未知時段 {unknown}（占計畫 {unknown / planned:.1%}），不列入分母也不算停機")
    print(f"可用率 A = {run} ÷ {known} = {availability:.1%}")
    print(f"效能 P = {TOTAL} × {IDEAL_CYCLE_S}s ÷ {run} = {performance:.1%}")
    print(f"品質 Q = {GOOD} ÷ {TOTAL} = {quality:.1%}")
    print(f"OEE = {availability * performance * quality:.1%}")
    print(f"若把未知當停機：A = {run / planned:.1%}，OEE = {run / planned * performance * quality:.1%}")
