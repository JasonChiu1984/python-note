"""依「當地日期」切批次視窗：遇到夏令時間切換，一天不一定是 24 小時；批次鍵用當地日期，重跑時冪等（標準函式庫）。"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def day_window(d: date, tz: ZoneInfo):
    start = datetime.combine(d, time(0), tz)
    end = datetime.combine(d + timedelta(days=1), time(0), tz)
    hours = (end.astimezone(timezone.utc) - start.astimezone(timezone.utc)) / timedelta(hours=1)
    return start, end, hours


class Store:
    def __init__(self):
        self.done: dict[str, float] = {}

    def run_batch(self, key, value):
        if key in self.done:
            return f"{key} 已完成，略過（冪等）"
        self.done[key] = value
        return f"{key} 寫入 {value}"


if __name__ == "__main__":
    for tzname, days in (("America/New_York", [date(2026, 3, 7), date(2026, 3, 8), date(2026, 11, 1)]),
                         ("Asia/Taipei", [date(2026, 3, 8)])):
        tz = ZoneInfo(tzname)
        for d in days:
            s, e, h = day_window(d, tz)
            print(f"{tzname:<17} {d} 視窗 {s:%H:%M %Z} → {e:%m-%d %H:%M %Z}，長度 {h:.0f} 小時")
    store = Store()
    for attempt in range(2):
        print(store.run_batch("site-a/daily-kwh/2026-11-01", 18_240.5))
    print("若以 24 小時累加來切日，11-01 這天會少算 1 小時、隔天多出 1 小時。")
