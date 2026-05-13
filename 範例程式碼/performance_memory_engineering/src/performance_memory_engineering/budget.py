from __future__ import annotations

from dataclasses import dataclass

from .profiling import BenchmarkResult, MemoryReport


@dataclass(frozen=True)
class PerformanceBudget:
    max_latency_ratio: float = 1.15
    max_peak_kib: float = 512.0


@dataclass(frozen=True)
class BudgetDecision:
    passed: bool
    latency_ratio: float
    peak_kib: float
    notes: tuple[str, ...]


def evaluate_budget(
    baseline: BenchmarkResult,
    candidate: BenchmarkResult,
    memory: MemoryReport,
    budget: PerformanceBudget,
) -> BudgetDecision:
    if baseline.median_seconds <= 0:
        raise ValueError("baseline median must be positive")
    latency_ratio = candidate.median_seconds / baseline.median_seconds
    notes: list[str] = []
    if latency_ratio > budget.max_latency_ratio:
        notes.append(f"latency ratio {latency_ratio:.3f} exceeds {budget.max_latency_ratio:.3f}")
    if memory.peak_kib > budget.max_peak_kib:
        notes.append(f"peak memory {memory.peak_kib:.3f} KiB exceeds {budget.max_peak_kib:.3f} KiB")
    if not notes:
        notes.append("performance budget passed")
    return BudgetDecision(
        passed=not any("exceeds" in note for note in notes),
        latency_ratio=round(latency_ratio, 3),
        peak_kib=memory.peak_kib,
        notes=tuple(notes),
    )
