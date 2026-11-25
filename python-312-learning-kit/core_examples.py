"""Runnable Python 3.12 core examples: one function for each C01–C16."""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
import importlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import TypedDict


def c01():
    value = 28
    if value >= 28:
        state = "high"
    else:
        state = "normal"
    return state == "high"


def c02():
    sensor = "溫度"
    value = 27.5
    wire = f"{sensor}={value:.1f}".encode("utf-8")
    return isinstance(wire, bytes) and wire.decode("utf-8") == "溫度=27.5"


def c03():
    original = [["AHU-01"]]
    alias = original
    shallow = original.copy()
    deep = deepcopy(original)
    alias[0].append("AHU-02")
    return shallow[0] == ["AHU-01", "AHU-02"] and deep[0] == ["AHU-01"]


def c04():
    return (5 + 2 * 3, 7 // 2, 7 % 2, 0 < 4 <= 4) == (11, 3, 1, True)


def c05():
    head, *rest = [24, 26, 24, 28]
    unique = set(rest)
    row = {"first": head, "last": rest[-1]}
    return (row, len(unique), [n for n in rest[1:] if n >= 25]) == (
        {"first": 24, "last": 28}, 3, [28]
    )


def c06():
    events = []
    for reading in [("offline", 0), ("ok", 28)]:
        match reading:
            case ("ok", value) if value >= 28:
                events.append("high")
                break
            case _:
                continue
    else:
        events.append("no alarm")
    return events == ["high"]


def c07():
    def scale(value, /, *offsets, factor=1, **tags):
        return value * factor + sum(offsets), tags["source"]
    return scale(10, 1, 2, factor=2, source="PLC") == (23, "PLC")


def c08():
    def counter():
        calls = 0
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                nonlocal calls
                calls += 1
                return calls, fn(*args, **kwargs)
            return wrapped
        return decorate
    @counter()
    def read():
        return 28
    return read() == (1, 28) and read() == (2, 28) and read.__name__ == "read"


def c09():
    @dataclass(frozen=True)
    class Sample:
        point: str
        value: float
        def __str__(self):
            return f"{self.point}={self.value:.1f}"
    return str(Sample("AHU-01", 27)) == "AHU-01=27.0"


def c10():
    def samples():
        yield 25
        yield from (26, 27)
    iterator = samples()
    return next(iterator) == 25 and list(iterator) == [26, 27] and list(iterator) == []


def c11():
    try:
        try:
            float("offline")
        except ValueError as exc:
            raise RuntimeError("bad sensor data") from exc
    except RuntimeError as exc:
        chained = isinstance(exc.__cause__, ValueError)
    labels = []
    try:
        raise ExceptionGroup("polling", [ValueError("bad input"), TimeoutError("late")])
    except* ValueError:
        labels.append("input")
    except* TimeoutError:
        labels.append("timeout")
    return chained and labels == ["input", "timeout"]


def c12():
    events = []
    @contextmanager
    def stream():
        events.append("open")
        try:
            yield 27.5
        finally:
            events.append("close")
    with stream() as value:
        events.append(value)
    return events == ["open", 27.5, "close"]


def c13():
    class Reading(TypedDict):
        point: str
        celsius: float
    row: Reading = {"point": "AHU-01", "celsius": 27.5}
    return row["celsius"] == 27.5


def c14():
    library = importlib.import_module("json")
    return library.loads("27") == 27 and bool(sys.executable)


def c15():
    with TemporaryDirectory() as temp:
        path = Path(temp) / "report.json"
        path.write_text(json.dumps({"設備": "AHU-01"}, ensure_ascii=False), encoding="utf-8")
        return json.loads(path.read_text(encoding="utf-8")) == {"設備": "AHU-01"}


async def c16():
    async def read(value):
        await asyncio.sleep(0)
        return value
    async with asyncio.TaskGroup() as group:
        a = group.create_task(read(25))
        b = group.create_task(read(26))
    return (a.result(), b.result()) == (25, 26)


def run():
    for chapter in range(1, 17):
        fn = globals()[f"c{chapter:02}"]
        result = asyncio.run(fn()) if chapter == 16 else fn()
        if result is not True:
            raise AssertionError(f"C{chapter:02} failed")
        print(f"C{chapter:02} OK")


if __name__ == "__main__":
    run()
