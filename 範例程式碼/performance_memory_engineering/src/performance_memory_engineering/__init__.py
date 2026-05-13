"""Performance and memory engineering sample package."""

from .budget import BudgetDecision, PerformanceBudget, evaluate_budget
from .profiling import BenchmarkResult, ProfileReport, run_benchmark, run_profile, run_memory_snapshot
from .workload import build_dataset, optimized_group_totals, slow_group_totals

__all__ = [
    "BenchmarkResult",
    "BudgetDecision",
    "PerformanceBudget",
    "ProfileReport",
    "build_dataset",
    "evaluate_budget",
    "optimized_group_totals",
    "run_benchmark",
    "run_memory_snapshot",
    "run_profile",
    "slow_group_totals",
]
