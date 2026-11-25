"""Deterministic Python benchmark; no network, packages or real device data."""
import argparse
import cProfile
import json
import math
import os
import platform
import pstats
import random
import statistics
import time
import tracemalloc


def fixture():
    rows = tuple((i, (19*i + 11) % 100_000) for i in range(3000))
    rng = random.Random(420)
    keys = tuple(rng.randrange(3300) for _ in range(200))
    return rows, keys


def baseline(rows, keys):
    return tuple(next((value for point, value in rows if point == key), None)
                 for key in keys)


def indexed(rows, keys):
    index = dict(rows)
    return tuple(index.get(key) for key in keys)


def nearest_rank(values, q):
    return sorted(values)[math.ceil(len(values) * q) - 1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=60)
    p.add_argument("--mode", choices=["timing", "profile", "memory"], default="timing")
    p.add_argument("--variant", choices=["baseline", "indexed"], default="baseline")
    args = p.parse_args()
    data = fixture()
    expected = baseline(*data)
    assert indexed(*data) == expected
    if args.mode == "profile":
        fn = baseline if args.variant == "baseline" else indexed
        with cProfile.Profile() as prof:
            for _ in range(60):
                fn(*data)
        pstats.Stats(prof).sort_stats("cumulative").print_stats(12)
        return
    if args.mode == "memory":
        for fn in (baseline, indexed):
            tracemalloc.start()
            try:
                result = fn(*data)
                current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            assert result == expected
            print(json.dumps({"variant": fn.__name__, "retained_bytes": current,
                              "traced_peak_bytes": peak}))
        return
    if args.samples < 40:
        p.error("--samples must be at least 40")
    timings = {fn.__name__: [] for fn in (baseline, indexed)}
    for _ in range(4):
        baseline(*data)
        indexed(*data)
    for i in range(args.samples):
        for fn in ((baseline, indexed) if i % 2 == 0 else (indexed, baseline)):
            start = time.perf_counter_ns()
            result = fn(*data)
            elapsed = time.perf_counter_ns() - start
            assert result == expected
            timings[fn.__name__].append(elapsed)
    print(json.dumps({
        "python": platform.python_version(), "implementation": platform.python_implementation(),
        "os": platform.system(), "kernel": platform.release(), "arch": platform.machine(),
        "logical_cpus_reported": os.cpu_count(), "samples_per_variant": args.samples,
        "clock_resolution_ns": time.get_clock_info("perf_counter").resolution * 1e9,
        "row_count": len(data[0]), "query_count": len(data[1]),
        "missing_count": expected.count(None),
        "results": {name: {"median_ns": statistics.median(t),
                           "p95_ns": nearest_rank(t, .95), "samples_ns": t}
                    for name, t in timings.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
