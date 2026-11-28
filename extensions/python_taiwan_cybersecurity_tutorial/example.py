"""資安事件通報時鐘：依《資通安全事件通報應變及演練辦法》的時限，從知悉時間算出各里程碑（教學工具）。

時限依本頁整理：知悉起 1 小時通報；第 1、2 級知悉起 72 小時、第 3、4 級（重大）36 小時內完成損害控制或復原。
本工具只算時間，不判斷是否構成事件、事件等級或適用身分；那些要依實際納管文件與法規判斷。
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def milestones(aware: datetime, level: int):
    if level not in (1, 2, 3, 4):
        raise ValueError("事件等級須為 1–4")
    control_h = 36 if level >= 3 else 72
    return [
        ("通報（知悉起 1 小時）", aware + timedelta(hours=1)),
        (f"完成損害控制或復原（知悉起 {control_h} 小時）", aware + timedelta(hours=control_h)),
    ]


def report_status(aware, reported, level):
    deadline = aware + timedelta(hours=1)
    late = reported - deadline
    if late <= timedelta(0):
        return "如期"
    minutes = -(-late // timedelta(minutes=1))    # 無條件進位：晚 59 秒也算逾時 1 分鐘
    return f"逾時 {minutes} 分鐘"


if __name__ == "__main__":
    # 冰水站監控異常：02:40 告警，03:15 資安人員確認為可疑遠端登入並「知悉」事件
    alarm = datetime(2026, 11, 28, 2, 40, tzinfo=TPE)
    aware = datetime(2026, 11, 28, 3, 15, tzinfo=TPE)
    print(f"第一筆告警：{alarm:%Y-%m-%d %H:%M %Z}（告警時間不等於知悉時間，兩者都要記錄）")
    print(f"知悉時間：  {aware:%Y-%m-%d %H:%M %Z}")
    for level in (2, 3):
        print(f"-- 若判定為第 {level} 級")
        for name, t in milestones(aware, level):
            print(f"   {name}：{t:%m-%d %H:%M}")
    reported = datetime(2026, 11, 28, 4, 5, tzinfo=TPE)
    print(f"實際通報 {reported:%H:%M}：{report_status(aware, reported, 3)}")
    utc = aware.astimezone(ZoneInfo("UTC"))
    print(f"跨國母公司若用 UTC 記錄，知悉時間是 {utc:%Y-%m-%d %H:%M %Z}，日期不同要特別注意")
