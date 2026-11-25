"""Compare task modes on CPython 3.12. Correctness demonstration, not a benchmark."""
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import sys


def squares(n):
    return sum(i * i for i in range(n))


async def two_reads():
    async def read(v):
        await asyncio.sleep(0.002)
        return v
    async with asyncio.TaskGroup() as tasks:
        a, b = (tasks.create_task(read(n)) for n in (25, 26))
    return [a.result(), b.result()]


def main():
    expected = [30, 55]
    inp = [5, 6]
    assert [squares(n) for n in inp] == expected
    assert asyncio.run(two_reads()) == [25, 26]
    with ThreadPoolExecutor(2) as pool:
        assert list(pool.map(squares, inp)) == expected
    with ProcessPoolExecutor(2) as pool:
        assert list(pool.map(squares, inp)) == expected
    print(f"CPython {sys.version.split()[0]}: serial, asyncio, thread, process OK")


if __name__ == "__main__":
    main()
