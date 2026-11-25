"""Reproducible standard-library CPython benchmark: simulated wait and pure-Python CPU."""

import argparse
import asyncio
from concurrent.futures import InterpreterPoolExecutor, ProcessPoolExecutor, ThreadPoolExecutor
from itertools import repeat
import json
import math
import multiprocessing
import os
import platform
import statistics
import sys
import sysconfig
from time import perf_counter_ns, sleep


def wait_job(delay):
    sleep(delay)
    return delay


def cpu_job(iterations):
    # Each step depends on the previous step; bounded integer size across modes.
    x = 123
    for _ in range(iterations):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
    return x


async def async_jobs(workload, values, workers):
    slots = asyncio.Semaphore(workers)

    async def one(value):
        async with slots:
            if workload == "wait":
                await asyncio.sleep(value)
                return value
            # Deliberately no await here: measure CPU work on the event loop.
            return cpu_job(value)

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(one(v)) for v in values]
    return [t.result() for t in tasks]


def cgroup_quota():
    try:
        with open("/sys/fs/cgroup/cpu.max", encoding="ascii") as f:
            return f.read().strip()
    except OSError:
        return None


def run(workers, repeats, tasks, delay, iterations, start):
    # Import by name to make worker callables resolvable across process/interpreter boundaries.
    import concurrency_platform_benchmark as target
    context = multiprocessing.get_context(start)
    available = getattr(os, "process_cpu_count", os.cpu_count)()
    result = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "available_cpu": available,
        "cpu_quota": cgroup_quota(),
        "free_thread_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "gil_enabled": sys._is_gil_enabled(),
        "process_start_method": context.get_start_method(),
        "workers": workers,
        "tasks": tasks,
        "repeats": repeats,
        "warmups": 1,
        "delay_seconds_per_task": delay,
        "cpu_iterations_per_task": iterations,
        "measurements": {},
    }

    with (asyncio.Runner() as runner,
          ThreadPoolExecutor(max_workers=workers) as threads,
          ProcessPoolExecutor(max_workers=workers, mp_context=context) as processes,
          InterpreterPoolExecutor(max_workers=workers) as interps):
        for workload, job, value in (("wait", target.wait_job, delay), ("cpu", target.cpu_job, iterations)):
            values = tuple(repeat(value, tasks))
            expected = [delay if workload == "wait" else job(value)] * tasks
            modes = {
                "serial": lambda: list(map(job, values)),
                "asyncio": lambda: runner.run(async_jobs(workload, values, workers)),
                "thread": lambda: list(threads.map(job, values)),
                "process": lambda: list(processes.map(job, values, chunksize=1)),
                "interpreter": lambda: list(interps.map(job, values)),
            }
            samples = {mode: [] for mode in modes}
            for i in range(repeats + 1):
                order = list(modes)
                order = order[i % len(order):] + order[:i % len(order)]
                for mode in order:
                    clock = perf_counter_ns()
                    observed = modes[mode]()
                    elapsed_ms = (perf_counter_ns() - clock) / 1e6
                    if observed != expected:
                        raise AssertionError((workload, mode, "incorrect result"))
                    if i:
                        samples[mode].append(elapsed_ms)
            result["measurements"][workload] = {
                mode: {"median_ms": round(statistics.median(v), 3),
                       "min_ms": round(min(v), 3), "max_ms": round(max(v), 3),
                       "raw_ms": [round(x, 3) for x in v]}
                for mode, v in samples.items()
            }
    result["gil_enabled_after"] = sys._is_gil_enabled()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--repeats", type=int, default=7)
    p.add_argument("--tasks", type=int, default=16)
    p.add_argument("--delay", type=float, default=.008)
    p.add_argument("--iterations", type=int, default=180000)
    p.add_argument("--start", choices=multiprocessing.get_all_start_methods(), default=None,
                   help="Use platform default when omitted")
    a = p.parse_args()
    if min(a.workers, a.repeats, a.tasks, a.iterations) < 1 or not math.isfinite(a.delay) or a.delay <= 0:
        p.error("workers, repeats, tasks, iterations and finite delay must be positive")
    print(json.dumps(run(a.workers, a.repeats, a.tasks, a.delay, a.iterations, a.start), indent=2))


if __name__ == "__main__":
    main()
