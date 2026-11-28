"""依目標主題與先修關係，產生學習順序並估算時數（graphlib.TopologicalSorter，標準函式庫）。"""
from graphlib import CycleError, TopologicalSorter

# 主題: (預估小時, 先修主題)
TOPICS = {
    "基礎語法": (12, []),
    "檔案與 CSV": (6, ["基礎語法"]),
    "函式與模組": (8, ["基礎語法"]),
    "例外與日誌": (6, ["函式與模組"]),
    "型別提示": (4, ["函式與模組"]),
    "測試 pytest": (8, ["函式與模組", "例外與日誌"]),
    "Pandas 資料整理": (16, ["檔案與 CSV", "函式與模組"]),
    "Modbus/BACnet 讀取": (12, ["例外與日誌", "型別提示"]),
    "非同步 asyncio": (10, ["函式與模組", "例外與日誌"]),
    "FastAPI 服務": (12, ["型別提示", "非同步 asyncio", "測試 pytest"]),
    "能源報表自動化": (10, ["Pandas 資料整理", "Modbus/BACnet 讀取"]),
}


def plan(goal):
    needed, stack = set(), [goal]
    while stack:                                   # 找出目標的所有先修主題
        t = stack.pop()
        if t not in needed:
            needed.add(t)
            stack.extend(TOPICS[t][1])
    ts = TopologicalSorter({t: TOPICS[t][1] for t in sorted(needed)})   # 排序讓結果可重現
    order = list(ts.static_order())
    return order, sum(TOPICS[t][0] for t in order)


if __name__ == "__main__":
    for goal in ("能源報表自動化", "FastAPI 服務"):
        order, hours = plan(goal)
        print(f"目標：{goal}（共 {len(order)} 個主題，約 {hours} 小時，每週 5 小時約 {-(-hours // 5)} 週）")
        for i, t in enumerate(order, 1):
            print(f"  {i:>2}. {t}（{TOPICS[t][0]} h）")
    TOPICS["基礎語法"] = (12, ["測試 pytest"])      # 故意造成循環依賴
    try:
        plan("測試 pytest")
    except CycleError as e:
        print("偵測到循環先修：", " → ".join(e.args[1]))
