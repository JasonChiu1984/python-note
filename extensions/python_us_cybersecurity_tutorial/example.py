"""美國多軌通報時鐘：SEC 8-K（4 個營業日）、HIPAA（60 日曆日）、FTC Safeguards（30 日）、
州法（NY 30 日、TX 個人 60 日／州檢察長 30 日）。只算日期，不判斷是否適用。

營業日排除週末與聯邦假日；假日以 2026–2027 年的聯邦假日（含週末遞延的 observed 日）計算。
"""
from datetime import date, timedelta


def nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def last_weekday(year, month, weekday):
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def observed(d):
    return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d


def federal_holidays(year):
    fixed = [date(year, 1, 1), date(year, 6, 19), date(year, 7, 4), date(year, 11, 11), date(year, 12, 25)]
    floating = [nth_weekday(year, 1, 0, 3), nth_weekday(year, 2, 0, 3), last_weekday(year, 5, 0),
                nth_weekday(year, 9, 0, 1), nth_weekday(year, 10, 0, 2), nth_weekday(year, 11, 3, 4)]
    return {observed(d) for d in fixed} | set(floating)


HOLIDAYS = federal_holidays(2026) | federal_holidays(2027)


def add_business_days(start, n):
    d = start
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS:
            n -= 1
    return d


if __name__ == "__main__":
    discovered = date(2026, 11, 20)        # 發現事件
    material = date(2026, 11, 24)          # 揭露委員會認定具重大性（週二）
    print(f"發現日 {discovered}，重大性認定日 {material}（{material:%a}）")
    print(f"SEC 8-K Item 1.05：認定後 4 個營業日 → {add_business_days(material, 4)}"
          f"（11/26 感恩節不計）")
    print(f"HIPAA 個人通知上限：發現後 60 日曆日 → {discovered + timedelta(days=60)}")
    print(f"FTC Safeguards（≥500 人）：發現後最遲 30 日 → {discovered + timedelta(days=30)}")
    print(f"紐約 GBL §899-aa：原則發現後 30 日內 → {discovered + timedelta(days=30)}")
    determined = date(2026, 11, 22)
    print(f"德州（認定外洩 {determined}）：州檢察長 30 日 → {determined + timedelta(days=30)}；"
          f"個人 60 日 → {determined + timedelta(days=60)}")
    print("2026 年聯邦假日：", ", ".join(d.strftime("%m-%d") for d in sorted(federal_holidays(2026))))
