"""中國大陸《國家網路安全事件報告管理辦法》初報時限計算（依本頁整理：關基 1 小時、
中央和國家機關 2 小時、其他網路營運者 4 小時；處置結束後 30 日內提交總結）。

另示範：資料出境前，用欄位清單初步標記可能屬於個人資訊的欄位，交給法遵複核。
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SHA = ZoneInfo("Asia/Shanghai")
LIMITS = {"關鍵資訊基礎設施營運者": 1, "中央和國家機關各部門及直屬單位": 2, "其他網路營運者": 4}

FIELDS = ["timestamp", "chiller_id", "chw_supply_temp", "operator_name", "badge_no",
          "remote_session_ip", "alarm_code", "phone"]
PI_HINTS = ("name", "badge", "phone", "ip", "account", "email", "id_no")


if __name__ == "__main__":
    found = datetime(2026, 11, 28, 9, 20, tzinfo=SHA)
    print(f"發現較大以上事件：{found:%Y-%m-%d %H:%M %Z}")
    for role, hours in LIMITS.items():
        print(f"  {role:<18} 初報最遲 {found + timedelta(hours=hours):%H:%M}")
    closed = datetime(2026, 12, 3, 18, 0, tzinfo=SHA)
    print(f"處置結束 {closed:%m-%d}，總結報告最遲 {closed + timedelta(days=30):%Y-%m-%d}")
    print()
    print("出境前欄位初篩（只是提示，不等於法律判斷）：")
    for f in FIELDS:
        flag = "可能為個人資訊，需複核" if any(h in f for h in PI_HINTS) else "—"
        print(f"  {f:<18} {flag}")
