"""Python 核心語法的 HVAC／監控資料範例與行為驗證。

執行：python3.15 core_syntax.py
只使用標準庫與模擬讀值。檔案測試使用 TemporaryDirectory。
受限環境若禁止事件迴圈需要的 socketpair，非同步整合測試會明確標示 skipped。
"""

import asyncio
import json
import keyword
import math
import socket
import sys
import unittest
from collections.abc import Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass, field
from decimal import Decimal
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol, TypedDict


def classify_temperature(value):
    if value is None:
        return "missing"
    elif value >= 28.0:
        return "high"
    else:
        return "normal"


def describe_event(event):
    match event:
        case {"kind": "temperature", "value": float(value)} if value >= 28:
            return f"高溫 {value:.1f} °C"
        case {"kind": "offline", "device": device}:
            return f"{device} 離線"
        case _:
            return "其他事件"


def summarize(device, /, offset=0.0, *samples, unit="°C", **metadata):
    """回傳平均值，額外資料置於獨立欄位以免覆寫固定欄位。"""
    if not samples:
        raise ValueError("至少需要一筆讀值")
    mean = sum(samples) / len(samples) + offset
    return {"device": device, "mean": mean, "unit": unit, "metadata": metadata}


def convert(raw, /, *, scale=0.1):
    return raw * scale


def collect(value, history=None):
    if history is None:
        history = []
    history.append(value)
    return history


def make_counter():
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment


UNIT = "°C"


def set_unit(unit):
    global UNIT
    UNIT = unit


def audit(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        return {"operation": fn.__name__, "result": result}

    return wrapper


@audit
def normalize(raw):
    """將十分之一度的原始資料轉成攝氏讀值。"""
    return raw / 10.0


@dataclass
class DeviceSnapshot:
    device: str
    temperature_c: float
    alarms: list[str] = field(default_factory=list)

    @property
    def temperature_f(self):
        return self.temperature_c * 9 / 5 + 32

    @classmethod
    def from_raw(cls, device, raw):
        return cls(device, raw / 10.0)

    @staticmethod
    def valid_name(name):
        return bool(name) and name.isascii()


@dataclass(frozen=True)
class FrozenSnapshot:
    device: str
    alarms: list[str] = field(default_factory=list)


class Sensor:
    def __init__(self, name):
        self.name = name


class CalibratedSensor(Sensor):
    def __init__(self, name, offset):
        super().__init__(name)
        self.offset = offset


class TrendSeries:
    def __init__(self, values):
        self._values = tuple(values)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, key):
        return self._values[key]

    def __repr__(self):
        return f"TrendSeries({self._values!r})"


def valid_values(rows):
    for row in rows:
        value = row.get("value")
        if value is not None:
            yield float(value)


def merge_batches(batches):
    for batch in batches:
        yield from batch


class InvalidReading(ValueError):
    pass


def parse_temperature(raw):
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidReading(f"無法解析溫度：{raw!r}") from exc
    else:
        return value


@contextmanager
def temporary_output(directory):
    with TemporaryDirectory(dir=directory) as owned_dir:
        yield Path(owned_dir) / "snapshot.tmp"


type PointMap = dict[str, float]


def first[T](items: Sequence[T]) -> T:
    if not items:
        raise ValueError("序列不可為空")
    return items[0]


class SampleBox[T]:
    def __init__(self, value: T):
        self.value = value


class Reader(Protocol):
    def read(self, point: str) -> float: ...


class Reading(TypedDict):
    point: str
    value: float
    quality: str


class MockReader:
    def read(self, point: str) -> float:
        return {"T10": 24.5, "T11": 25.0}[point]


def read_point(reader: Reader, point: str) -> float:
    return reader.read(point)


def checked_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("讀值必須是數字，且不可是 bool")
    return float(value)


async def read_simulated(point: str) -> tuple[str, float]:
    await asyncio.sleep(0)
    return point, 24.5


async def collect_async() -> dict[str, float]:
    async with asyncio.TaskGroup() as group:
        tasks = [
            group.create_task(read_simulated(point))
            for point in ("T10", "T11", "T12")
        ]
    return dict(task.result() for task in tasks)


async def simulated_stream():
    for value in (24.0, 24.5, 25.0):
        await asyncio.sleep(0)
        yield value


async def summarize_stream():
    values = []
    async for value in simulated_stream():
        values.append(value)
    return sum(values) / len(values)


class CoreSyntaxTests(unittest.TestCase):
    def test_keywords_and_indentation(self):
        self.assertTrue(keyword.iskeyword("class"))
        self.assertTrue(keyword.issoftkeyword("match"))
        self.assertFalse(keyword.iskeyword("list"))
        namespace = {}
        exec("supply_c = 7.2\nif supply_c < 8:\n    state = 'ok'\n", namespace)
        self.assertEqual(namespace["state"], "ok")

    def test_numeric_types_and_decimal(self):
        self.assertEqual(10**30 + 1, 1000000000000000000000000000001)
        self.assertEqual(-3 // 2, -2)
        self.assertEqual(-3 % 2, 1)
        self.assertTrue(math.isclose(0.1 + 0.2, 0.3))
        self.assertEqual(Decimal("0.1") + Decimal("0.2"), Decimal("0.3"))

    def test_fstrings_text_and_bytes(self):
        point, value = "T10", 24.375
        self.assertEqual(f"{point}: {value:.1f} °C", "T10: 24.4 °C")
        self.assertEqual(f"{{point}} = {point}", "{point} = T10")
        self.assertEqual("送風溫度".encode("utf-8").decode("utf-8"), "送風溫度")
        frame = bytes([1, 3, 0, 32])
        self.assertEqual(frame[0], 1)
        self.assertEqual(int.from_bytes(frame[2:4], "big"), 32)
        mutable = bytearray(frame)
        mutable[0] = 2
        self.assertEqual(frame[0], 1)

    def test_alias_shallow_and_deep_copy(self):
        original = {"AHU01": {"setpoint": 24.0}}
        alias, shallow, deep = original, original.copy(), deepcopy(original)
        original["AHU01"]["setpoint"] = 25.0
        self.assertIs(alias, original)
        self.assertIsNot(shallow, original)
        self.assertEqual(shallow["AHU01"]["setpoint"], 25.0)
        self.assertEqual(deep["AHU01"]["setpoint"], 24.0)

    def test_nested_list_construction(self):
        shared = [[0] * 3] * 2
        independent = [[0] * 3 for _ in range(2)]
        shared[0][0] = independent[0][0] = 9
        self.assertEqual(shared[1][0], 9)
        self.assertEqual(independent[1][0], 0)

    def test_identity_and_mutable_contents_of_tuple(self):
        first_list, second_list = [24.0], [24.0]
        self.assertEqual(first_list, second_list)
        self.assertIsNot(first_list, second_list)
        frozen_outer = (first_list,)
        frozen_outer[0].append(25.0)
        self.assertEqual(frozen_outer, ([24.0, 25.0],))

    def test_operators_and_zero_default(self):
        self.assertEqual(-2**2, -4)
        self.assertEqual(2**-2, 0.25)
        self.assertTrue((0b1010 & 0b0010) != 0)
        reading = 0.0
        self.assertEqual(reading or 24.0, 24.0)
        self.assertEqual(24.0 if reading is None else reading, 0.0)
        self.assertTrue(0 <= 50 <= 100)

    def test_slice_unpack_and_comprehension(self):
        values = [23.5, 24.0, 24.5, 25.0]
        first_value, *middle, last = values
        self.assertEqual((first_value, middle, last), (23.5, [24.0, 24.5], 25.0))
        self.assertEqual(values[-2:], [24.5, 25.0])
        self.assertEqual(values[::2], [23.5, 24.5])
        self.assertEqual([v for v in values if v >= 24.5], [24.5, 25.0])
        with self.assertRaises(ValueError):
            _ = values[::0]

    def test_dict_merge_and_strict_zip(self):
        self.assertEqual({**{"mode": "auto"}, **{"mode": "manual"}}, {"mode": "manual"})
        self.assertEqual(dict(zip(["T10"], [24.0], strict=True)), {"T10": 24.0})
        with self.assertRaises(ValueError):
            list(zip(["T10", "T11"], [24.0], strict=True))

    def test_sort_mutates_and_returns_none(self):
        values = [25.0, 23.0]
        result = values.sort()
        self.assertIsNone(result)
        self.assertEqual(values, [23.0, 25.0])

    def test_if_and_match(self):
        self.assertEqual(classify_temperature(None), "missing")
        self.assertEqual(classify_temperature(0.0), "normal")
        self.assertEqual(classify_temperature(29.0), "high")
        self.assertEqual(describe_event({"kind": "temperature", "value": 29.0}), "高溫 29.0 °C")
        self.assertEqual(describe_event({"kind": "temperature", "value": "29.0"}), "其他事件")
        self.assertEqual(describe_event({"kind": "offline", "device": "AHU02"}), "AHU02 離線")

    def test_loop_else_and_break(self):
        def first_alarm(values):
            for value in values:
                if value > 28:
                    break
            else:
                return None
            return value
        self.assertIsNone(first_alarm([24.0, 25.0]))
        self.assertIsNone(first_alarm([]))
        self.assertEqual(first_alarm([24.0, 29.0, 30.0]), 29.0)

    def test_complete_function_signature(self):
        result = summarize("AHU01", 0.2, 24.0, 26.0, unit="°C", floor=3)
        self.assertEqual(result["device"], "AHU01")
        self.assertAlmostEqual(result["mean"], 25.2)
        self.assertEqual(result["metadata"], {"floor": 3})
        self.assertAlmostEqual(convert(245, scale=0.1), 24.5)
        with self.assertRaises(TypeError):
            convert(raw=245)
        with self.assertRaises(TypeError):
            convert(245, 0.1)
        with self.assertRaises(ValueError):
            summarize("AHU01")

    def test_default_list_is_not_shared(self):
        a, b = collect(24.0), collect(25.0)
        self.assertEqual(a, [24.0])
        self.assertEqual(b, [25.0])
        self.assertIsNot(a, b)
        existing = [23.0]
        self.assertIs(collect(24.0, existing), existing)

    def test_lambda_and_closure(self):
        ranked = sorted([("T10", 25.0), ("T11", 23.0)], key=lambda item: item[1])
        self.assertEqual(ranked[0][0], "T11")
        counter = make_counter()
        self.assertEqual((counter(), counter()), (1, 2))
        late = [lambda: i for i in range(3)]
        bound = [lambda i=i: i for i in range(3)]
        self.assertEqual([fn() for fn in late], [2, 2, 2])
        self.assertEqual([fn() for fn in bound], [0, 1, 2])

    def test_global_and_local_binding(self):
        previous = UNIT
        try:
            set_unit("K")
            self.assertEqual(UNIT, "K")
        finally:
            set_unit(previous)
        def local_error():
            value += 1
            return value
        with self.assertRaises(UnboundLocalError):
            local_error()

    def test_decorator_preserves_metadata(self):
        self.assertEqual(normalize(245), {"operation": "normalize", "result": 24.5})
        self.assertEqual(normalize.__name__, "normalize")
        self.assertIn("攝氏", normalize.__doc__)

    def test_dataclass_property_and_factories(self):
        snap = DeviceSnapshot.from_raw("AHU01", 245)
        self.assertEqual(snap.temperature_c, 24.5)
        self.assertAlmostEqual(snap.temperature_f, 76.1)
        self.assertTrue(DeviceSnapshot.valid_name("AHU01"))
        self.assertFalse(DeviceSnapshot.valid_name(""))
        another = DeviceSnapshot("AHU02", 25.0)
        snap.alarms.append("HIGH")
        self.assertEqual(another.alarms, [])

    def test_frozen_is_not_deep_freeze(self):
        snap = FrozenSnapshot("AHU01")
        with self.assertRaises(FrozenInstanceError):
            snap.device = "AHU02"
        snap.alarms.append("HIGH")
        self.assertEqual(snap.alarms, ["HIGH"])

    def test_super_and_structural_protocol_use(self):
        sensor = CalibratedSensor("T10", 0.2)
        self.assertEqual((sensor.name, sensor.offset), ("T10", 0.2))
        self.assertEqual(read_point(MockReader(), "T10"), 24.5)

    def test_custom_container_protocol(self):
        values = TrendSeries([24.0, 25.0])
        self.assertEqual(len(values), 2)
        self.assertEqual(list(values), [24.0, 25.0])
        self.assertEqual(values[-1], 25.0)
        self.assertEqual(repr(values), "TrendSeries((24.0, 25.0))")

    def test_generator_exhaustion(self):
        stream = valid_values([{"value": "24.1"}, {"value": None}, {"value": "25.3"}])
        self.assertEqual(next(stream), 24.1)
        self.assertEqual(list(stream), [25.3])
        self.assertEqual(list(stream), [])
        with self.assertRaises(StopIteration):
            next(stream)

    def test_yield_from(self):
        self.assertEqual(list(merge_batches([[24.0, 25.0], [26.0]])), [24.0, 25.0, 26.0])
        def inner():
            yield 24.0
            return "complete"
        def outer():
            status = yield from inner()
            yield status
        self.assertEqual(list(outer()), [24.0, "complete"])

    def test_exception_cause(self):
        self.assertEqual(parse_temperature("24.5"), 24.5)
        with self.assertRaises(InvalidReading) as caught:
            parse_temperature("offline")
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_try_else_finally(self):
        events = []
        try:
            events.append("try")
        except ValueError:
            events.append("except")
        else:
            events.append("else")
        finally:
            events.append("finally")
        self.assertEqual(events, ["try", "else", "finally"])

    def test_exception_group_splits_by_type(self):
        handled = []
        try:
            raise ExceptionGroup("採樣失敗", [ValueError("T10"), TimeoutError("AHU02")])
        except* ValueError as group:
            handled.append(("value", len(group.exceptions)))
        except* TimeoutError as group:
            handled.append(("timeout", len(group.exceptions)))
        self.assertEqual(handled, [("value", 1), ("timeout", 1)])

    def test_context_cleanup_on_success(self):
        with TemporaryDirectory() as directory:
            existing = Path(directory) / "snapshot.tmp"
            existing.write_text("既有資料", encoding="utf-8")
            with temporary_output(directory) as path:
                path.write_text("24.5", encoding="utf-8")
                self.assertTrue(path.exists())
                self.assertNotEqual(path, existing)
            self.assertFalse(path.exists())
            self.assertEqual(existing.read_text(encoding="utf-8"), "既有資料")

    def test_context_cleanup_on_error(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "模擬失敗"):
                with temporary_output(directory) as path:
                    path.write_text("24.5", encoding="utf-8")
                    raise RuntimeError("模擬失敗")
            self.assertFalse(path.exists())

    def test_type_alias_generics_and_typed_dict(self):
        self.assertEqual(first(["T10", "T11"]), "T10")
        self.assertEqual(first((24.5, 25.0)), 24.5)
        with self.assertRaises(ValueError):
            first([])
        box = SampleBox[float](24.5)
        self.assertEqual(box.value, 24.5)
        record: Reading = {"point": "T10", "value": 24.5, "quality": "good"}
        self.assertIs(type(record), dict)
        self.assertEqual(PointMap.__value__, dict[str, float])

    def test_object_narrowing(self):
        self.assertEqual(checked_number(24), 24.0)
        self.assertEqual(checked_number(24.5), 24.5)
        with self.assertRaises(TypeError):
            checked_number(True)
        with self.assertRaises(TypeError):
            checked_number("24.5")

    def test_json_file_roundtrip(self):
        snapshot = {"device": "AHU01", "label": "送風", "temperature_c": 24.5, "online": True}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            with path.open("w", encoding="utf-8") as file:
                json.dump(snapshot, file, ensure_ascii=False, indent=2, allow_nan=False)
            self.assertIn("送風", path.read_text(encoding="utf-8"))
            with path.open("r", encoding="utf-8") as file:
                self.assertEqual(json.load(file), snapshot)

    def test_json_nonfinite_and_tuple_conversion(self):
        with self.assertRaises(ValueError):
            json.dumps({"temperature_c": float("nan")}, allow_nan=False)
        self.assertEqual(json.loads(json.dumps(("T10", 24.5))), ["T10", 24.5])

    def test_async_taskgroup_and_async_iteration(self):
        # 只探測本機 socketpair 能力，不對任何服務建立網路連線。
        try:
            read_end, write_end = socket.socketpair()
        except PermissionError as exc:
            self.skipTest(f"環境禁止事件迴圈所需的 socketpair：{exc}")
        else:
            read_end.close()
            write_end.close()
        async def check_async():
            readings = await collect_async()
            mean = await summarize_stream()
            return readings, mean
        readings, mean = asyncio.run(check_async())
        self.assertEqual(readings, {"T10": 24.5, "T11": 24.5, "T12": 24.5})
        self.assertEqual(mean, 24.5)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CoreSyntaxTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({
        "python": sys.version.split()[0],
        "tests_run": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
    }, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
