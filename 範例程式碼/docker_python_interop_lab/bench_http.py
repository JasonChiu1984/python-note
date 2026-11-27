"""僅量測本機合成 /sample；不連設備、不重試、不接受遠端主機。"""
import argparse
import csv
import http.client
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter_ns

HEADER = ("attempt", "start_ns", "elapsed_ms", "status", "result")


def one(port, attempt):
    start = perf_counter_ns()
    status = None
    result = "contract"
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", "/sample", headers={"Connection": "close"})
        with conn.getresponse() as response:
            status = response.status
            raw = response.read(65537)
            if status != 200:
                result = "http_status"
            elif len(raw) > 65536 or response.headers.get_content_type() != "application/json":
                result = "response_format"
            else:
                body = json.loads(raw)
                if (
                    isinstance(body, dict) and type(body.get("schema")) is int
                    and body["schema"] == 1 and body.get("point") == "supply_temp"
                    and body.get("unit") == "degC" and body.get("quality") == "synthetic"
                    and type(body.get("value")) in (int, float) and body["value"] == 7.2
                ):
                    result = "ok"
    except (OSError, ValueError, http.client.HTTPException) as exc:
        result = type(exc).__name__
    finally:
        conn.close()
    elapsed_ms = (perf_counter_ns() - start) / 1e6
    return attempt, start, elapsed_ms, status, result


def quantile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(q * len(ordered)) - 1]


def measure(port, workers, count, warmup):
    if not 1 <= port <= 65535 or not 1 <= workers <= 8 or not 1 <= count <= 2000 or not 0 <= warmup <= 100:
        raise ValueError("invalid local-lab parameter")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        warm = list(pool.map(lambda i: one(port, i), range(warmup)))
        start = perf_counter_ns()
        rows = list(pool.map(lambda i: one(port, i), range(1, count + 1)))
        seconds = (perf_counter_ns() - start) / 1e9
    success = [r[2] for r in rows if r[4] == "ok"]
    return rows, {
        "attempts": count, "success": len(success), "failures": count - len(success),
        "warmup_failures": sum(r[4] != "ok" for r in warm),
        "failure_ratio": (count - len(success)) / count,
        "seconds": seconds, "success_per_s": len(success) / seconds,
        "p50_ms_success_only": quantile(success, 0.50),
        "p95_ms_success_only": quantile(success, 0.95),
        "p99_ms_success_only": quantile(success, 0.99),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=18080)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--count", type=int, default=400)
    p.add_argument("--warmup", type=int, default=32)
    p.add_argument("--csv", type=Path, required=True)
    a = p.parse_args()
    try:
        with a.csv.open("x", newline="", encoding="utf-8") as out:
            rows, summary = measure(a.port, a.workers, a.count, a.warmup)
            writer = csv.writer(out)
            writer.writerow(HEADER)
            writer.writerows(rows)
    except (ValueError, OSError) as exc:
        p.error(str(exc))
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return int(bool(summary["failures"] or summary["warmup_failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
