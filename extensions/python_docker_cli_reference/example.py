"""解析 docker ps／inspect 的 JSON 輸出，找出重啟中、沒有健康檢查或以 root 執行的容器（標準函式庫）。

實際使用：docker ps -a --format '{{json .}}' > ps.jsonl；docker inspect $(docker ps -aq) > inspect.json
"""
import json

PS_JSONL = """{"Names":"bms-gateway","Image":"bms/gateway:2.4.1","State":"running","Status":"Up 3 days (healthy)"}
{"Names":"modbus-poller","Image":"bms/poller:latest","State":"restarting","Status":"Restarting (1) 12 seconds ago"}
{"Names":"influxdb","Image":"influxdb:2.7","State":"running","Status":"Up 3 days"}"""

INSPECT = [
    {"Name": "/bms-gateway", "Config": {"User": "app", "Healthcheck": {"Test": ["CMD", "python", "-m", "health"]}},
     "RestartCount": 0, "HostConfig": {"RestartPolicy": {"Name": "unless-stopped"}, "Memory": 268435456}},
    {"Name": "/modbus-poller", "Config": {"User": "", "Healthcheck": None},
     "RestartCount": 147, "HostConfig": {"RestartPolicy": {"Name": "always"}, "Memory": 0}},
    {"Name": "/influxdb", "Config": {"User": "", "Healthcheck": None},
     "RestartCount": 0, "HostConfig": {"RestartPolicy": {"Name": "no"}, "Memory": 0}},
]


def findings():
    ps = {row["Names"]: row for row in map(json.loads, PS_JSONL.splitlines())}
    for c in INSPECT:
        name = c["Name"].lstrip("/")
        issues = []
        if ps[name]["State"] == "restarting" or c["RestartCount"] > 5:
            issues.append(f"重啟 {c['RestartCount']} 次，先看 docker logs --tail 50 {name}")
        if not c["Config"]["Healthcheck"]:
            issues.append("沒有 HEALTHCHECK")
        if c["Config"]["User"] in ("", "root", "0"):
            issues.append("以 root 執行")
        if c["HostConfig"]["Memory"] == 0:
            issues.append("未設定記憶體上限")
        if ps[name]["Image"].endswith(":latest"):
            issues.append("使用 :latest；請另記錄實際映像 ID 或 digest")
        if c["HostConfig"]["RestartPolicy"]["Name"] == "no":
            issues.append("重開機後不會自動啟動")
        yield name, issues


if __name__ == "__main__":
    for name, issues in findings():
        print(f"{name}: {'OK' if not issues else ''}")
        for i in issues:
            print(f"  - {i}")
