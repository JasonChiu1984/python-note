"""有界佇列、背壓與正常關閉。可在一般或 free-threaded CPython 執行。"""

import asyncio
import queue
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor


def thread_pipeline() -> None:
    incoming = queue.Queue(maxsize=2)
    outgoing = queue.SimpleQueue()
    jobs = tuple(range(8))

    def worker() -> None:
        while True:
            try:
                value = incoming.get()
            except queue.ShutDown:
                return
            try:
                outgoing.put((value, value * value))
            finally:
                incoming.task_done()

    with ThreadPoolExecutor(max_workers=2) as pool:
        workers = [pool.submit(worker) for _ in range(2)]
        try:
            for value in jobs:
                incoming.put(value, timeout=5)
        finally:
            incoming.shutdown()
        for future in workers:
            future.result(timeout=5)
        incoming.join()

    actual = sorted(outgoing.get_nowait() for _ in jobs)
    assert actual == [(value, value * value) for value in jobs]
    assert outgoing.empty()  # 所有 producer 已結束，此時才檢查有無剩餘結果。


async def async_pipeline() -> None:
    incoming = asyncio.Queue(maxsize=1)
    outgoing = []

    async def worker() -> None:
        while True:
            try:
                value = await incoming.get()
            except asyncio.QueueShutDown:
                return
            try:
                outgoing.append(value * value)
            finally:
                incoming.task_done()

    async with asyncio.timeout(5):
        async with asyncio.TaskGroup() as group:
            group.create_task(worker())
            for value in range(4):
                await incoming.put(value)
            incoming.shutdown()
            await incoming.join()

    assert outgoing == [0, 1, 4, 9]


async def completed_tasks_keep_identity() -> None:
    async def read(value: float) -> float:
        await asyncio.sleep(0)
        return value

    async with asyncio.TaskGroup() as group:
        by_task = {
            group.create_task(read(value)): point
            for point, value in (("T10", 24.5), ("T11", 31.2))
        }
        readings = {}
        async for task in asyncio.as_completed(by_task):
            readings[by_task[task]] = await task

    assert readings == {"T10": 24.5, "T11": 31.2}


def main() -> None:
    disabled_at_build = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    print(f"{sys.version.split()[0]} free-threaded build={disabled_at_build} GIL enabled={sys._is_gil_enabled()}")
    thread_pipeline()
    print("PASS thread_pipeline")
    asyncio.run(async_pipeline())
    print("PASS async_pipeline")
    asyncio.run(completed_tasks_keep_identity())
    print("PASS completed_tasks_keep_identity")


if __name__ == "__main__":
    main()
