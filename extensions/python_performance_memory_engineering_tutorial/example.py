"""先量再改：cProfile 找熱點、tracemalloc 比較記憶體、正確性不變（標準函式庫）。輸出只印排名與比例，不印絕對時間。"""
import cProfile
import pstats
import tracemalloc
from functools import lru_cache

POINTS = [f"B{b}-AHU{a:02d}-{p}" for b in range(1, 6) for a in range(1, 41) for p in ("SAT", "RAT", "MAT", "DMP", "FAN")]


def parse_slow(tag):
    parts = tag.split("-")
    building = int(parts[0][1:])
    ahu = int(parts[1][3:])
    kinds = {"SAT": "溫度", "RAT": "溫度", "MAT": "溫度", "DMP": "開度", "FAN": "狀態"}   # 每次呼叫都重建
    return building, ahu, kinds[parts[2]]


KINDS = {"SAT": "溫度", "RAT": "溫度", "MAT": "溫度", "DMP": "開度", "FAN": "狀態"}


@lru_cache(maxsize=None)
def parse_fast(tag):
    b, a, p = tag.split("-")
    return int(b[1:]), int(a[3:]), KINDS[p]


def report(parse):
    out = {}
    for _ in range(20):                           # 模擬每輪重複解析
        for t in POINTS:
            b, a, kind = parse(t)
            out[kind] = out.get(kind, 0) + 1
    return out


if __name__ == "__main__":
    prof = cProfile.Profile()
    prof.enable()
    r1 = report(parse_slow)
    prof.disable()
    stats = pstats.Stats(prof)
    calls = {k[2]: v[1] for k, v in stats.stats.items() if k[2] in ("parse_slow", "report")}
    print("cProfile 呼叫次數：", calls, "（實際排查時用 sort_stats('cumulative') 看耗時排名）")
    r2 = report(parse_fast)
    print("結果一致：", r1 == r2, r1)
    print("lru_cache 命中：", parse_fast.cache_info().hits, "次，未命中：", parse_fast.cache_info().misses, "次")
    tracemalloc.start()
    as_list = [t.split("-") for t in POINTS]
    mid = tracemalloc.get_traced_memory()[0]
    as_tuple = [tuple(t.split("-")) for t in POINTS]
    end = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    print(f"list 版與 tuple 版記憶體比：約 {mid / (end - mid):.1f} 倍")
