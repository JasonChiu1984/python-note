from __future__ import annotations

import unittest

from performance_memory_engineering.budget import PerformanceBudget, evaluate_budget
from performance_memory_engineering.profiling import BenchmarkResult, run_benchmark, run_memory_snapshot, run_profile
from performance_memory_engineering.workload import build_dataset, optimized_group_totals, slow_group_totals


class PerformanceMemoryEngineeringTests(unittest.TestCase):
    def test_optimized_result_matches_baseline(self) -> None:
        readings = build_dataset(400)
        self.assertEqual(slow_group_totals(readings), optimized_group_totals(readings))

    def test_benchmark_reports_result_size(self) -> None:
        readings = build_dataset(240)
        result = run_benchmark("optimized", lambda: optimized_group_totals(readings), iterations=3)
        self.assertEqual(result.result_size, 4)
        self.assertGreater(result.median_seconds, 0)

    def test_profile_reports_top_functions(self) -> None:
        readings = build_dataset(240)
        report = run_profile("optimized", lambda: optimized_group_totals(readings), top_n=3)
        self.assertEqual(len(report.top_functions), 3)
        self.assertGreater(report.total_calls, 0)

    def test_memory_snapshot_reports_peak(self) -> None:
        readings = build_dataset(240)
        report = run_memory_snapshot("optimized", lambda: optimized_group_totals(readings))
        self.assertEqual(report.result_size, 4)
        self.assertGreater(report.peak_kib, 0)

    def test_budget_passes_for_fast_candidate(self) -> None:
        baseline = BenchmarkResult("slow", 3, 0.010, 0.009, 0.011, 4)
        candidate = BenchmarkResult("optimized", 3, 0.004, 0.003, 0.005, 4)
        memory = run_memory_snapshot("optimized", lambda: optimized_group_totals(build_dataset(100)))
        decision = evaluate_budget(baseline, candidate, memory, PerformanceBudget(max_latency_ratio=1.15, max_peak_kib=512))
        self.assertTrue(decision.passed)

    def test_budget_fails_for_regression(self) -> None:
        baseline = BenchmarkResult("baseline", 3, 0.010, 0.009, 0.011, 4)
        candidate = BenchmarkResult("candidate", 3, 0.020, 0.019, 0.021, 4)
        memory = run_memory_snapshot("candidate", lambda: optimized_group_totals(build_dataset(100)))
        decision = evaluate_budget(baseline, candidate, memory, PerformanceBudget(max_latency_ratio=1.15, max_peak_kib=512))
        self.assertFalse(decision.passed)
        self.assertIn("latency ratio", decision.notes[0])


if __name__ == "__main__":
    unittest.main()
