"""最小權限政策決策點（PDP）：預設拒絕，每筆請求依身分、裝置狀態、資源、動作與時間窗判斷（標準函式庫）。"""
from datetime import datetime

POLICIES = [
    {"role": "vendor", "action": "read", "resource": "ahu/*", "device_ok": True,
     "ticket": True, "hours": (8, 18)},
    {"role": "operator", "action": "read", "resource": "*", "device_ok": True},
    {"role": "operator", "action": "write", "resource": "ahu/*/setpoint", "device_ok": True, "mfa": True},
]


def match(pattern, resource):
    p, r = pattern.split("/"), resource.split("/")
    if pattern == "*":
        return True
    return len(p) == len(r) and all(a in ("*", b) for a, b in zip(p, r)) or (p[-1] == "*" and r[:len(p) - 1] == p[:-1])


def decide(req):
    for pol in POLICIES:
        if pol["role"] != req["role"] or pol["action"] != req["action"] or not match(pol["resource"], req["resource"]):
            continue
        if pol.get("device_ok") and not req["device_ok"]:
            return "拒絕：裝置狀態不符（未更新或未受管）"
        if pol.get("mfa") and not req.get("mfa"):
            return "拒絕：寫入需要 MFA"
        if pol.get("ticket") and not req.get("ticket"):
            return "拒絕：需要有效工單"
        if "hours" in pol and not pol["hours"][0] <= req["time"].hour < pol["hours"][1]:
            return f"拒絕：不在允許時段 {pol['hours'][0]}–{pol['hours'][1]} 時"
        return "允許"
    return "拒絕：沒有符合的政策（預設拒絕）"


if __name__ == "__main__":
    day, night = datetime(2026, 11, 28, 10), datetime(2026, 11, 28, 22)
    reqs = [
        ("廠商白天唯讀", dict(role="vendor", action="read", resource="ahu/01/sat", device_ok=True, ticket=True, time=day)),
        ("廠商夜間唯讀", dict(role="vendor", action="read", resource="ahu/01/sat", device_ok=True, ticket=True, time=night)),
        ("廠商嘗試寫入", dict(role="vendor", action="write", resource="ahu/01/setpoint", device_ok=True, ticket=True, time=day)),
        ("廠商無工單", dict(role="vendor", action="read", resource="ahu/01/sat", device_ok=True, ticket=False, time=day)),
        ("值班寫入無 MFA", dict(role="operator", action="write", resource="ahu/01/setpoint", device_ok=True, time=night)),
        ("值班寫入有 MFA", dict(role="operator", action="write", resource="ahu/01/setpoint", device_ok=True, mfa=True, time=night)),
        ("值班筆電未更新", dict(role="operator", action="read", resource="chiller/02/kw", device_ok=False, time=day)),
    ]
    for name, r in reqs:
        print(f"{name:<10} {r['action']:<5} {r['resource']:<16} → {decide(r)}")
