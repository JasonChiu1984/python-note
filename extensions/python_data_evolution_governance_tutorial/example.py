"""資料結構演進：每筆紀錄帶 schema 版本，讀取時逐版升級到最新結構；舊資料不改寫也能讀（標準函式庫）。"""
import json

RECORDS = [
    '{"v": 1, "point": "AHU1_SAT", "value": 22.5}',
    '{"v": 2, "point": "AHU1_SAT", "value": 22.6, "unit": "C"}',
    '{"v": 3, "point_id": "AHU1_SAT", "value": 22.7, "unit": "degC", "quality": "good"}',
    '{"v": 4, "point_id": "AHU1_SAT", "value": 22.8}',
]


def v1_to_v2(r):
    return {**r, "v": 2, "unit": "C"}                     # v1 沒有單位欄位，當時一律是攝氏


def v2_to_v3(r):
    r = dict(r)
    r["point_id"] = r.pop("point")                       # 欄位改名
    r["unit"] = {"C": "degC", "F": "degF"}[r["unit"]]    # 單位改用 UCUM 風格代碼
    r["quality"] = "unknown"                             # 新欄位：舊資料沒有品質資訊
    r["v"] = 3
    return r


UPGRADES = {1: v1_to_v2, 2: v2_to_v3}
LATEST = 3


def load(line):
    r = json.loads(line)
    if r["v"] > LATEST:
        raise ValueError(f"版本 {r['v']} 比程式支援的 {LATEST} 新，請先升級讀取程式")
    while r["v"] < LATEST:
        r = UPGRADES[r["v"]](r)
    return r


if __name__ == "__main__":
    for line in RECORDS:
        try:
            print(load(line))
        except ValueError as e:
            print("拒絕：", e)
