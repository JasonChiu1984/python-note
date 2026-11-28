"""多台設備設定點變更的工作流：狀態轉移表、逾時、部分失敗時依相反順序補償（標準函式庫）。"""

TRANSITIONS = {
    ("draft", "approve"): "approved",
    ("approved", "apply"): "applying",
    ("applying", "all_ok"): "done",
    ("applying", "failed"): "compensating",
    ("compensating", "rolled_back"): "rolled_back",
}


class Workflow:
    def __init__(self, changes):
        self.state, self.changes, self.applied, self.log = "draft", changes, [], []

    def fire(self, event):
        nxt = TRANSITIONS.get((self.state, event))
        if nxt is None:
            raise ValueError(f"狀態 {self.state} 不接受事件 {event}")
        self.log.append(f"{self.state} --{event}--> {nxt}")
        self.state = nxt

    def run(self, devices):
        self.fire("approve")
        self.fire("apply")
        for dev, new in self.changes:
            old = devices[dev]["sp"]
            if devices[dev].get("offline"):
                self.log.append(f"  {dev} 寫入逾時（離線）")
                self.fire("failed")
                for d, prev in reversed(self.applied):           # 依相反順序補償
                    devices[d]["sp"] = prev
                    self.log.append(f"  補償 {d} → 回復 {prev}")
                self.fire("rolled_back")
                return
            devices[dev]["sp"] = new
            self.applied.append((dev, old))
            self.log.append(f"  {dev} {old} → {new}")
        self.fire("all_ok")


if __name__ == "__main__":
    plan = [("CH-01", 7.5), ("CH-02", 7.5), ("CH-03", 7.5)]
    for title, offline in (("全部在線", None), ("CH-03 離線", "CH-03")):
        devs = {d: {"sp": 7.0} for d, _ in plan}
        if offline:
            devs[offline]["offline"] = True
        wf = Workflow(plan)
        wf.run(devs)
        print(f"== {title}：最終狀態 {wf.state}")
        print("\n".join(wf.log))
        print("設定點：", {d: v["sp"] for d, v in devs.items()})
    try:
        Workflow(plan).fire("apply")
    except ValueError as e:
        print("非法轉移：", e)
