"""HVAC 遙測演練：純合成 I/O，不連設備、不送控制命令。Python 3.11+。"""
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from itertools import islice
import json
from math import isfinite
import unittest


@dataclass(frozen=True, slots=True)
class Snapshot:
    room: str
    temperature_c: float

    @property
    def high(self):
        return self.temperature_c >= 28.0


def command(message):
    match message:
        case {"op": "observe", "limit": int(n), **rest} if type(n) is int and 1 <= n <= 10 and not rest:
            return n
        case _:
            raise ValueError("僅接受 observe，limit 為 1 到 10 的整數")


def examples():
    # 模擬工作清單有 3 筆；本次只取前兩筆。
    yield ("AHU-01", 26.4)
    yield ("AHU-02", 29.2)
    yield ("AHU-03", 27.5)


async def read(sample):
    room, value = sample
    await asyncio.sleep(0)  # 交還事件迴圈，沒有真實 I/O 或網路延遲。
    if not isfinite(value):
        raise ValueError(f"{room} 讀值不合法")
    return Snapshot(room, value)


@contextmanager
def buffer():
    stream = StringIO()
    try:
        yield stream
    finally:
        stream.close()


async def collect(message, source=None):
    # 本函式每次呼叫應取得一個新來源，不共用可變 iterator。
    limit = command(message)
    selected = tuple(islice(examples() if source is None else source, limit))
    async with asyncio.timeout(2):
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(read(sample)) for sample in selected]
    snapshots = tuple(task.result() for task in tasks)
    with buffer() as stream:
        for s in snapshots:
            row = {"room": s.room, "temperature_c": s.temperature_c, "high": s.high}
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        return stream.getvalue()


class Checks(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_reads(self):
        def source():
            yield ("AHU-02", 29.2)
            raise AssertionError("不應多讀")
        data = await collect({"op": "observe", "limit": 1}, source())
        self.assertEqual(json.loads(data), {"room": "AHU-02", "temperature_c": 29.2, "high": True})

    async def test_order_and_threshold(self):
        data = await collect({"op": "observe", "limit": 2}, examples())
        rows = [json.loads(line) for line in data.splitlines()]
        self.assertEqual([row["room"] for row in rows], ["AHU-01", "AHU-02"])
        self.assertEqual([row["high"] for row in rows], [False, True])

    async def test_reject_boolean_and_write_command(self):
        for invalid in ({"op": "observe", "limit": True}, {"op": "control", "limit": 2}):
            with self.assertRaises(ValueError):
                await collect(invalid, iter(()))

    async def test_bad_sample_reports_group_failure(self):
        with self.assertRaises(ExceptionGroup) as caught:
            await collect({"op": "observe", "limit": 2}, iter([("AHU-01", float("nan"))]))
        self.assertTrue(any(isinstance(exc, ValueError) for exc in caught.exception.exceptions))

    def test_resource_cleanup(self):
        with self.assertRaises(RuntimeError):
            with buffer() as out:
                raise RuntimeError("故障後仍須收尾")
        self.assertTrue(out.closed)


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    else:
        print(asyncio.run(collect({"op": "observe", "limit": 2}, examples())), end="")
