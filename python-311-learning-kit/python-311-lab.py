"""Offline CPython 3.11+ lab: python python-311-lab.py."""
import asyncio
import sys
import tomllib
from typing import NotRequired, TypedDict, Self


class Settings(TypedDict):
    workers: int
    label: NotRequired[str]


class Batch:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, item: str) -> Self:
        self.items.append(item)
        return self


def settings(text: str) -> Settings:
    raw = tomllib.loads(text)
    workers = raw.get("workers")
    if type(workers) is not int or not 1 <= workers <= 32:
        exc = ValueError("workers must be an integer from 1 to 32")
        exc.add_note("Use the top-level workers key in the TOML configuration.")
        raise exc
    return {"workers": workers}


def grouped() -> list[tuple[str, int]]:
    handled = []
    try:
        raise ExceptionGroup("batch", [ValueError("bad input"), OSError("offline")])
    except* ValueError as exc:
        handled.append(("input", len(exc.exceptions)))
    except* OSError as exc:
        handled.append(("io", len(exc.exceptions)))
    return handled


async def bounded_batch() -> list[str]:
    async def run(value: str) -> str:
        await asyncio.sleep(0)
        return value

    async with asyncio.timeout(1):
        async with asyncio.TaskGroup() as tasks:
            a = tasks.create_task(run("A"))
            b = tasks.create_task(run("B"))
        return [a.result(), b.result()]


async def deadline() -> bool:
    try:
        async with asyncio.timeout(0):
            await asyncio.sleep(0)
    except TimeoutError:
        return True
    return False


def main() -> None:
    assert settings("workers = 4") == {"workers": 4}
    try:
        settings("workers = true")
    except ValueError as exc:
        assert "top-level workers key" in exc.__notes__[0]
    else:
        raise AssertionError("bool must not be accepted as a worker count")
    assert grouped() == [("input", 1), ("io", 1)]
    assert asyncio.run(bounded_batch()) == ["A", "B"]
    assert asyncio.run(deadline())
    assert Batch().add("A").add("B").items == ["A", "B"]
    print(f"Python {sys.version.split()[0]}: 6 checks passed")


if __name__ == "__main__":
    main()
