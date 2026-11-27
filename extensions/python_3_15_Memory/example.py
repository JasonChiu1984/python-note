"""用 tracemalloc 比較三種存放 10 萬筆讀值的方式，並示範 frozendict 作為不可變設定的記憶與雜湊行為。"""
import sys
import tracemalloc
from array import array

N = 100_000


def measure(build):
    tracemalloc.start()
    obj = build()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return obj, current


if __name__ == "__main__":
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    rows = [
        ("list[float]", lambda: [20.0 + i * 0.001 for i in range(N)]),
        ("array('d')", lambda: array("d", (20.0 + i * 0.001 for i in range(N)))),
        ("list[dict]", lambda: [{"ts": i, "v": 20.0 + i * 0.001} for i in range(N)]),
    ]
    base = None
    for name, build in rows:
        _, cur = measure(build)
        base = base or cur
        print(f"{name:<12} 約 {cur / 1024 / 1024:5.1f} MiB（{cur / base:4.1f} 倍）")
    cfg = frozendict(device="AHU-01", unit_id=3, scale=0.1)
    cache = {cfg: "已解析的點位設定"}                # frozendict 可雜湊，可當字典鍵或快取鍵
    print("frozendict 當快取鍵：", cache[frozendict(scale=0.1, device="AHU-01", unit_id=3)])
    try:
        cfg["scale"] = 1.0
    except TypeError as e:
        print("修改 frozendict：", type(e).__name__)
    print("產生新版本：", cfg | {"scale": 0.01})
