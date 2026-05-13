from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from performance_memory_engineering.budget import PerformanceBudget, evaluate_budget
from performance_memory_engineering.profiling import run_benchmark, run_memory_snapshot, run_profile
from performance_memory_engineering.workload import build_dataset, optimized_group_totals, slow_group_totals


def main() -> int:
    readings = build_dataset(1600)
    slow_result = slow_group_totals(readings)
    optimized_result = optimized_group_totals(readings)
    if slow_result != optimized_result:
        raise SystemExit("optimized result does not match baseline")

    baseline = run_benchmark("slow_group_totals", lambda: slow_group_totals(readings))
    candidate = run_benchmark("optimized_group_totals", lambda: optimized_group_totals(readings))
    profile = run_profile("optimized_group_totals", lambda: optimized_group_totals(readings))
    memory = run_memory_snapshot("optimized_group_totals", lambda: optimized_group_totals(readings))
    decision = evaluate_budget(candidate, baseline, memory, PerformanceBudget(max_latency_ratio=1.15, max_peak_kib=512))

    report = {
        "baseline": baseline.__dict__,
        "candidate": candidate.__dict__,
        "profile_top_functions": profile.top_functions,
        "profile_total_calls": profile.total_calls,
        "memory": memory.__dict__,
        "budget": decision.__dict__,
    }
    evidence_path = PROJECT_ROOT / "performance_evidence.json"
    evidence_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if not decision.passed:
        raise SystemExit("; ".join(decision.notes))

    print("performance memory smoke passed: benchmark + profile + tracemalloc + budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
