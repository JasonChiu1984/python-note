"""Python 3.15 並行 API 功能示範；不進行效能排名或硬體基準測試。

執行：
    python3.15 concurrency_315.py
    python3.15t concurrency_315.py

本範例沒有連接真實設備，也不發送控制命令。
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from concurrent import interpreters
from concurrent.futures import InterpreterPoolExecutor, ThreadPoolExecutor


def collect_squares(source):
    """每個 worker 的結果留在自己的區域串列。"""
    return [value * value for value in source]


@threading.synchronized_iterator
def measurements(count):
    """3.15 新裝飾器：同一次呼叫產生的 iterator 可由多個 thread 消費。"""
    yield from range(count)


def check_shared_iterator(source, count):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(collect_squares, source) for _ in range(2)]
        per_worker = [future.result() for future in futures]
    combined = [value for batch in per_worker for value in batch]
    assert sorted(combined) == [value * value for value in range(count)]
    return {"items": len(combined), "no_duplicates_or_missing": True}


def check_concurrent_tee():
    """3.15 新函式：每個 consumer 各自收到完整串流。"""
    left, right = threading.concurrent_tee(range(5), 2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(list, branch) for branch in (left, right)]
        results = [future.result() for future in futures]
    assert results == [list(range(5)), list(range(5))]
    return {"each_consumer_received": results}


def interpreter_sender(output_queue, samples):
    """此函式在另一個 interpreter 執行，不依賴主 interpreter 的全域變數。"""
    output_queue.put(sum(samples) / len(samples))


def check_interpreter_queue():
    """跨 interpreter 的 queue 自 3.14 起提供；不是 3.15 新語法。"""
    output_queue = interpreters.create_queue(maxsize=1)
    interpreter = interpreters.create()
    thread = None
    try:
        thread = interpreter.call_in_thread(
            interpreter_sender, output_queue, (20.0, 22.0, 24.0)
        )
        average = output_queue.get(timeout=10)
        thread.join()
        assert average == 22.0
        return {"average": average, "queue_api": "concurrent.interpreters.Queue"}
    finally:
        # 結束 thread 後才能關閉其 interpreter。
        if thread is not None:
            thread.join()
        interpreter.close()


def check_interpreter_pool():
    """3.14 起可用。使用可序列化的內建函式與資料避免 REPL/closure 限制。"""
    with InterpreterPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(pow, [2, 3, 5], [10, 10, 10]))
    assert results == [1024, 59049, 9765625]
    return {"results": results}


async def simulated_read(name, value):
    # 讓出事件迴圈以示範協作式排程；這不是網路通訊或時間保證。
    await asyncio.sleep(0)
    return {"point": name, "value": value}


async def check_task_group():
    """TaskGroup 自 3.11 起可用；async/await 自 3.5 起可用。"""
    async with asyncio.TaskGroup() as group:
        tasks = [
            group.create_task(simulated_read("T10", 24.5)),
            group.create_task(simulated_read("T11", 25.0)),
        ]
    results = [task.result() for task in tasks]
    assert [item["value"] for item in results] == [24.5, 25.0]
    return {"readings": results}


def runtime_information():
    jit = getattr(sys, "_jit", None)
    return {
        "version": sys.version,
        "executable": sys.executable,
        "free_threaded_build": sys.abi_info.free_threaded,
        "gil_enabled": sys._is_gil_enabled(),
        "isolated_interpreters_supported": sys.implementation.supports_isolated_interpreters,
        "jit_available": jit.is_available() if jit is not None else False,
        "jit_enabled": jit.is_enabled() if jit is not None else False,
    }


def main():
    count = 40
    results = {
        "runtime_before": runtime_information(),
        "serialize_iterator_315": check_shared_iterator(
            threading.serialize_iterator(range(count)), count
        ),
        "synchronized_iterator_315": check_shared_iterator(measurements(count), count),
        "concurrent_tee_315": check_concurrent_tee(),
        "interpreter_queue_since_314": check_interpreter_queue(),
        "interpreter_pool_since_314": check_interpreter_pool(),
        "task_group_since_311": asyncio.run(check_task_group()),
        "runtime_after": runtime_information(),
        "status": "PASS",
        "measurement_scope": "functional correctness only; no performance benchmark",
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
