"""Offline executor and cancellation checks, no performance claims."""
import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


def squares(value: int) -> int:
    return value * value


async def exercise() -> None:
    release = asyncio.Event()
    cleanup = asyncio.Event()

    async def pending():
        try:
            release.set()
            await asyncio.Future()
        finally:
            cleanup.set()

    async def failing():
        await release.wait()
        raise ValueError("simulated error")

    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(pending())
            group.create_task(failing())
    except* ValueError as errors:
        assert len(errors.exceptions) == 1
    else:
        raise AssertionError("expected a child failure")
    assert cleanup.is_set()

    try:
        async with asyncio.timeout(0):
            await asyncio.sleep(0)
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected deadline expiry")


if __name__ == "__main__":
    asyncio.run(exercise())
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(squares, [1, 2, 3])) == [1, 4, 9]
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as pool:
        assert list(pool.map(squares, [1, 2, 3])) == [1, 4, 9]
    print("4 concurrency scenarios passed: cleanup, deadline, threads, processes")
