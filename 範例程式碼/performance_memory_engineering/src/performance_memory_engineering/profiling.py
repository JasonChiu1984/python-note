from __future__ import annotations

import cProfile
import io
import pstats
import statistics
import time
import tracemalloc
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    iterations: int
    median_seconds: float
    min_seconds: float
    max_seconds: float
    result_size: int


@dataclass(frozen=True)
class ProfileReport:
    function_name: str
    top_functions: list[str]
    total_calls: int


@dataclass(frozen=True)
class MemoryReport:
    function_name: str
    current_kib: float
    peak_kib: float
    result_size: int


def run_benchmark(name: str, fn: Callable[[], dict[str, float]], iterations: int = 7) -> BenchmarkResult:
    if iterations < 3:
        raise ValueError("iterations must be at least 3")
    durations: list[float] = []
    result: dict[str, float] = {}
    for _ in range(iterations):
        start = time.perf_counter()
        result = fn()
        durations.append(time.perf_counter() - start)
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        median_seconds=statistics.median(durations),
        min_seconds=min(durations),
        max_seconds=max(durations),
        result_size=len(result),
    )


def run_profile(function_name: str, fn: Callable[[], T], top_n: int = 5) -> ProfileReport:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    profiler = cProfile.Profile()
    profiler.enable()
    fn()
    profiler.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).strip_dirs().sort_stats("cumulative")
    stats.print_stats(top_n)
    lines = [line.strip() for line in stats_stream.getvalue().splitlines() if line.strip()]
    return ProfileReport(function_name=function_name, top_functions=lines[-top_n:], total_calls=stats.total_calls)


def run_memory_snapshot(function_name: str, fn: Callable[[], dict[str, float]]) -> MemoryReport:
    tracemalloc.start()
    try:
        result = fn()
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return MemoryReport(
        function_name=function_name,
        current_kib=round(current / 1024, 3),
        peak_kib=round(peak / 1024, 3),
        result_size=len(result),
    )
