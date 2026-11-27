"""依 python.org 公布的支援週期（以月為單位），查詢某日期各版本的狀態，並找出已過支援期的環境（標準函式庫）。"""
from datetime import date

# 版本: (首次發布日, 進入僅安全修正的年月, 結束支援的年月)；依 python.org 與各版本 PEP，核對日 2026-11-28
RELEASES = {
    "3.10": (date(2021, 10, 4), (2023, 4), (2026, 10)),
    "3.11": (date(2022, 10, 24), (2024, 4), (2027, 10)),
    "3.12": (date(2023, 10, 2), (2025, 4), (2028, 10)),
    "3.13": (date(2024, 10, 7), (2026, 10), (2029, 10)),
    "3.14": (date(2025, 10, 7), (2027, 10), (2030, 10)),
    "3.15": (date(2026, 10, 9), (2028, 10), (2031, 10)),
}


def ym(d):
    return (d.year, d.month)


def status(ver, on):
    first, sec, eol = RELEASES[ver]
    if on < first:
        return "尚未發布"
    if ym(on) >= eol:
        return "已結束支援"
    if ym(on) >= sec:
        return "僅安全修正"
    return "錯誤修正（bugfix）"


def months_left(ver, on):
    y, m = RELEASES[ver][2]
    return (y - on.year) * 12 + (m - on.month)


if __name__ == "__main__":
    today = date(2026, 11, 28)
    print(f"{today} 各版本狀態：")
    for v in RELEASES:
        y, m = RELEASES[v][2]
        print(f"  Python {v:<5} {status(v, today):<12} 支援至 {y}-{m:02d}")
    fleet = {"能源報表伺服器": "3.10", "BACnet 閘道器": "3.11", "分析筆電": "3.13", "CI": "3.14"}
    print("專案環境檢查：")
    for host, v in fleet.items():
        left = months_left(v, today)
        note = "已過期，優先升級" if left <= 0 else f"約剩 {left} 個月"
        print(f"  {host:<10} Python {v}：{status(v, today)}，{note}")
