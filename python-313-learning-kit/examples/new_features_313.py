"""在 CPython 3.13 或更新版本執行 3.13 語言與標準函式庫示範。"""

import argparse
import base64
import copy
import dbm.sqlite3
import itertools
from contextlib import redirect_stderr
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ReadOnly, TypedDict, TypeIs


def local_snapshot() -> None:
    threshold = 28
    snapshot = locals()
    snapshot["threshold"] = 99
    assert threshold == 28
    assert locals()["threshold"] == 28
    assert snapshot is not locals()


@dataclass(frozen=True)
class Limits:
    low_c: float
    high_c: float


def replace_record() -> None:
    original = Limits(18.0, 28.0)
    updated = copy.replace(original, high_c=30.0)
    assert (original.high_c, updated.high_c) == (28.0, 30.0)


class Sample[T = float]:
    def __init__(self, value: T) -> None:
        self.value = value


class Reading(TypedDict):
    sensor: ReadOnly[str]
    value: float


def is_text(value: str | bytes) -> TypeIs[str]:
    return isinstance(value, str)


def normalize(value: str | bytes) -> str:
    if is_text(value):
        return value.strip()
    return value.decode("utf-8").strip()


def typing_contract() -> None:
    sample: Sample = Sample(24.5)
    assert sample.value == 24.5
    assert Sample.__type_params__[0].__default__ is float
    assert Reading.__readonly_keys__ == {"sensor"}
    assert normalize(" T10 ") == normalize(b" T10 ") == "T10"


def strict_batches() -> None:
    assert list(itertools.batched([1, 2, 3, 4], 2, strict=True)) == [(1, 2), (3, 4)]
    try:
        list(itertools.batched([1, 2, 3], 2, strict=True))
    except ValueError:
        pass
    else:
        raise AssertionError("不完整的批次應回報 ValueError")


def deprecated_option() -> None:
    parser = argparse.ArgumentParser(prog="monitor")
    parser.add_argument("--legacy", action="store_true", deprecated=True)
    output = StringIO()
    with redirect_stderr(output):
        assert parser.parse_args([]).legacy is False
        assert output.getvalue() == ""
        assert parser.parse_args(["--legacy"]).legacy is True
    assert "--legacy" in output.getvalue()


def z85_round_trip() -> None:
    payload = b"AHU1"
    encoded = base64.z85encode(payload)
    assert len(encoded) == 5
    assert base64.z85decode(encoded) == payload


def sqlite_dbm_round_trip() -> None:
    with TemporaryDirectory() as directory:
        path = Path(directory) / "points.db"
        with dbm.sqlite3.open(path, "c") as store:
            store[b"T10"] = b"24.5"
        with dbm.sqlite3.open(path, "r") as store:
            assert store[b"T10"] == b"24.5"


if __name__ == "__main__":
    for demo in (
        local_snapshot,
        replace_record,
        typing_contract,
        strict_batches,
        deprecated_option,
        z85_round_trip,
        sqlite_dbm_round_trip,
    ):
        demo()
        print(f"PASS {demo.__name__}")
