"""歐盟多軌通報時鐘：NIS2（24h／72h／1 個月）、CRA Article 14（24h／72h／14 天或 1 個月）、
GDPR（72h）。只計算期限，不判斷事件是否「重大」或產品是否落入範圍。
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
CET = ZoneInfo("Europe/Berlin")


def add_month(dt):
    """「1 個月」以曆月計算；月底日期不存在時取該月最後一天。"""
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    for day in (dt.day, 30, 29, 28):
        try:
            return dt.replace(year=y, month=m, day=day)
        except ValueError:
            continue


def after(dt, **delta):
    """在 UTC 上加時間再轉回當地時間。

    Python 對同一時區的 aware datetime 做加法時採「牆上時間」運算，跨越夏令時間切換會差一小時；
    先轉 UTC 才是經過的真實時間。
    """
    return (dt.astimezone(UTC) + timedelta(**delta)).astimezone(dt.tzinfo)


def show(label, dt):
    print(f"  {label:<46} {dt.astimezone(CET):%Y-%m-%d %H:%M %Z}")


if __name__ == "__main__":
    aware = datetime(2026, 1, 30, 22, 30, tzinfo=CET)      # 營運者知悉重大事件
    print(f"知悉時間：{aware:%Y-%m-%d %H:%M %Z}（= {aware.astimezone(UTC):%H:%M UTC}）")
    print("NIS2 Article 23（重大事件）")
    show("早期預警（24 小時內）", after(aware, hours=24))
    show("事件通報（72 小時內）", after(aware, hours=72))
    final = add_month(after(aware, hours=72))
    show("最終報告（事件通報後 1 個月內）", final)
    print("CRA Article 14（製造商：遭積極利用的漏洞）")
    show("早期預警（24 小時內）", after(aware, hours=24))
    show("漏洞通報（72 小時內）", after(aware, hours=72))
    fix_available = datetime(2026, 2, 6, 10, 0, tzinfo=CET)
    show("最終報告（修正措施可用後 14 天內）", after(fix_available, days=14))
    print("GDPR Article 33（個資侵害，控制者）")
    show("通報監管機關（72 小時內）", after(aware, hours=72))
    print("注意：1 月 30 日加 1 個月不是 2 月 30 日，", add_month(datetime(2026, 1, 30, tzinfo=CET)).date())
    dst = datetime(2026, 3, 29, 1, 30, tzinfo=CET)          # 當天 02:00 切換為夏令時間
    print(f"夏令時間切換：{dst:%m-%d %H:%M %Z} 直接加 24h = {dst + timedelta(hours=24):%m-%d %H:%M %Z}（只過了 23 小時）；"
          f"經 UTC 計算 = {after(dst, hours=24):%m-%d %H:%M %Z}")
