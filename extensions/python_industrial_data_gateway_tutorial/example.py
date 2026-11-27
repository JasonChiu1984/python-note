"""閘道器的資料品質標記：把原始讀值、倍率、單位與品質一起傳出，而不是只傳一個數字（標準函式庫）。

規則：通訊失敗 → bad；值超出儀表量程 → uncertain；超過資料年齡上限 → stale；其他 → good。
"""
import json
from dataclasses import asdict, dataclass

POINTS = {
    "AHU1_SAT": {"scale": 0.1, "unit": "degC", "range": (-20, 60), "max_age_s": 30},
    "CH1_KW": {"scale": 1, "unit": "kW", "range": (0, 500), "max_age_s": 30},
}


@dataclass
class Sample:
    point: str
    raw: int | None
    value: float | None
    unit: str
    quality: str
    source_ts: int
    age_s: int


def tag(point, raw, source_ts, now, comm_ok=True):
    cfg = POINTS[point]
    age = now - source_ts
    if not comm_ok or raw is None:
        return Sample(point, None, None, cfg["unit"], "bad", source_ts, age)
    value = round(raw * cfg["scale"], 3)
    lo, hi = cfg["range"]
    q = "uncertain" if not lo <= value <= hi else "stale" if age > cfg["max_age_s"] else "good"
    return Sample(point, raw, value, cfg["unit"], q, source_ts, age)


if __name__ == "__main__":
    now = 1_795_800_100
    out = [
        tag("AHU1_SAT", 225, now - 4, now),
        tag("AHU1_SAT", 225, now - 95, now),
        tag("AHU1_SAT", 32767, now - 3, now),
        tag("CH1_KW", None, now - 2, now, comm_ok=False),
        tag("CH1_KW", 168, now - 1, now),
    ]
    for s in out:
        print(json.dumps(asdict(s), ensure_ascii=False))
    good = [s for s in out if s.quality == "good"]
    print(f"可直接用於計算的筆數：{len(good)} / {len(out)}")
