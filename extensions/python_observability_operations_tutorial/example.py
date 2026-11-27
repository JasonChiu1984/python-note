"""從結構化日誌計算 SLI：成功率、P95 延遲、錯誤預算消耗（標準函式庫）。"""
import json
from statistics import quantiles

LOG = """\
{"ts":"10:00:01","event":"poll","device":"M01","ok":true,"ms":42}
{"ts":"10:00:01","event":"poll","device":"M02","ok":true,"ms":51}
{"ts":"10:00:02","event":"poll","device":"M03","ok":false,"ms":1000,"err":"timeout"}
{"ts":"10:00:06","event":"poll","device":"M01","ok":true,"ms":39}
{"ts":"10:00:06","event":"poll","device":"M02","ok":true,"ms":47}
{"ts":"10:00:07","event":"poll","device":"M03","ok":false,"ms":1000,"err":"timeout"}
{"ts":"10:00:11","event":"poll","device":"M01","ok":true,"ms":44}
{"ts":"10:00:11","event":"poll","device":"M02","ok":true,"ms":180}
{"ts":"10:00:12","event":"poll","device":"M03","ok":true,"ms":61}
{"ts":"10:00:12","event":"config_reload","by":"ops"}
"""
SLO_SUCCESS = 0.99                       # 目標：99% 輪詢成功


if __name__ == "__main__":
    polls = [r for r in map(json.loads, LOG.splitlines()) if r["event"] == "poll"]
    ok = sum(r["ok"] for r in polls)
    rate = ok / len(polls)
    lat = [r["ms"] for r in polls if r["ok"]]
    p95 = quantiles(lat, n=20, method="inclusive")[-1]
    budget = 1 - SLO_SUCCESS
    burn = (1 - rate) / budget
    print(f"輪詢 {len(polls)} 次，成功率 {rate:.1%}（SLO {SLO_SUCCESS:.0%}）")
    print(f"成功請求延遲 P95 = {p95:.0f} ms，最大 {max(lat)} ms")
    print(f"錯誤預算消耗速率 {burn:.1f} 倍（> 1 代表照此速度會在期限前耗盡）")
    by_dev = {}
    for r in polls:
        by_dev.setdefault(r["device"], []).append(r["ok"])
    print("各設備成功率：", {d: f"{sum(v) / len(v):.0%}" for d, v in sorted(by_dev.items())})
    errs = [(r["ts"], r["device"], r["err"]) for r in polls if not r["ok"]]
    print("錯誤事件：", errs)
