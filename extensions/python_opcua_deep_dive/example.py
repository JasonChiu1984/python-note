"""OPC UA 整合契約的三個基本功：NodeId 解析、StatusCode 分級、DataValue 時效判斷（標準函式庫）。"""
import re
from datetime import datetime, timedelta, timezone

NODEID = re.compile(r"(?:ns=(?P<ns>\d+)|nsu=(?P<nsu>[^;]+));(?P<kind>[isgb])=(?P<id>.+)")


def parse_nodeid(text):
    m = NODEID.fullmatch(text)
    if not m:
        if text.startswith(("i=", "s=")):          # 省略 ns 代表 namespace 0
            kind, ident = text.split("=", 1)
            return {"ns": 0, "kind": kind, "id": ident}
        raise ValueError(f"無法解析 NodeId：{text}")
    d = m.groupdict()
    return {"ns": int(d["ns"]) if d["ns"] else None, "nsu": d["nsu"], "kind": d["kind"], "id": d["id"]}


def severity(status_code: int):
    """StatusCode 最高兩個位元：00 Good、01 Uncertain、10 Bad。"""
    return {0: "Good", 1: "Uncertain", 2: "Bad"}.get(status_code >> 30, "Reserved")


def freshness(source_ts, server_ts, now, max_age=timedelta(seconds=30)):
    if source_ts is None:
        return "無來源時間，只能依伺服器時間判斷"
    age = now - source_ts
    lag = server_ts - source_ts
    verdict = "過期" if age > max_age else "新鮮"
    return f"{verdict}（來源時間距今 {age.total_seconds():.0f}s，伺服器延遲 {lag.total_seconds():.0f}s）"


if __name__ == "__main__":
    for t in ("ns=2;s=AHU01.SAT", "nsu=urn:example:plant;s=AHU01.SAT", "i=2258", "ns=3;i=1001", "AHU01.SAT"):
        try:
            print(f"{t:<36} → {parse_nodeid(t)}")
        except ValueError as e:
            print(f"{t:<36} → {e}")
    for code in (0x00000000, 0x40920000, 0x80340000, 0x808A0000):
        print(f"StatusCode 0x{code:08X} → {severity(code)}")
    now = datetime(2026, 11, 28, 10, 0, 0, tzinfo=timezone.utc)
    print(freshness(now - timedelta(seconds=5), now - timedelta(seconds=4), now))
    print(freshness(now - timedelta(minutes=10), now - timedelta(seconds=2), now))
