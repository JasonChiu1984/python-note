"""Python 3.15 新特性：無第三方套件的可執行學習範例。

執行：python3.15 new_features_315.py
本檔使用 3.15 新語法，舊版 Python 會在解析階段拒絕；不需要連線設備。
型別註記示範與執行期資料驗證分開，程式不會冒充靜態型別檢查器。
"""

lazy import fractions as lazy_fractions

import ast
import base64
import copy
import json
import math
import math.integer
import pickle
import re
import sys
import tomllib
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeForm, TypedDict, disjoint_base


MISSING = sentinel("MISSING")


class DeviceConfig(TypedDict, closed=True):
    name: str
    timeout: float


class Measurements(TypedDict, extra_items=float):
    device: str


@disjoint_base
class ConfigurationBase:
    pass


@disjoint_base
class TransportBase:
    pass


def describe_setting(value: float | None | MISSING = MISSING) -> str:
    """缺省、明確清除、實際數值是三個不同狀態。"""
    if value is MISSING:
        return "沿用原設定"
    if value is None:
        return "清除此設定"
    return f"更新設定為 {value}"


def expect_error(error_type: type[Exception], action) -> None:
    """驗證教學中預期失敗的操作，不讓整份範例中斷。"""
    try:
        action()
    except error_type:
        return
    raise AssertionError(f"預期 {error_type.__name__}，操作卻成功")


def demo_lazy_import() -> None:
    """第一次讀取延遲名稱才完成匯入；模組若已載入則可重用。"""
    loaded_before_use = "fractions" in sys.modules
    result = lazy_fractions.Fraction(1, 8)
    assert result.numerator == 1 and result.denominator == 8
    assert "fractions" in sys.modules
    expect_error(
        SyntaxError,
        lambda: compile("def f():\n    lazy import json\n", "<invalid-lazy>", "exec"),
    )
    print(f"  fractions 第一次使用前已載入：{loaded_before_use}；使用結果：{result}")


def demo_unpacking() -> None:
    batches = [(23.4, 24.1), (25.2,), ()]
    values = [*batch for batch in batches]
    unique = {*batch for batch in batches}
    stream = (*batch for batch in batches)
    parts = [{"AHU01": 23.4}, {"AHU02": 25.2}, {"AHU01": 23.8}]
    latest = {**part for part in parts}
    assert values == [23.4, 24.1, 25.2]
    assert unique == {23.4, 24.1, 25.2}
    assert list(stream) == values
    assert latest == {"AHU01": 23.8, "AHU02": 25.2}
    assert [*part for part in [[[1]], [[2]]]] == [[1], [2]]


def demo_frozendict() -> None:
    config = frozendict(device="AHU01", timeout=1.5)
    assert config["timeout"] == 1.5
    assert not isinstance(config, dict)
    assert {config: "已驗證"}[config] == "已驗證"
    assert config == frozendict(timeout=1.5, device="AHU01")

    def mutate() -> None:
        config["timeout"] = 2.0

    expect_error(TypeError, mutate)
    nested = frozendict(samples=[])
    nested["samples"].append(24.5)
    assert nested["samples"] == [24.5]
    expect_error(TypeError, lambda: hash(nested))


def demo_sentinel() -> None:
    assert describe_setting() == "沿用原設定"
    assert describe_setting(None) == "清除此設定"
    assert describe_setting(0.0) == "更新設定為 0.0"
    assert bool(MISSING) is True
    assert sentinel("MISSING") is not MISSING
    assert copy.copy(MISSING) is MISSING
    assert copy.deepcopy(MISSING) is MISSING
    assert pickle.loads(pickle.dumps(MISSING)) is MISSING
    local_marker = sentinel("LOCAL_ONLY", repr="<未提供>")
    assert repr(local_marker) == "<未提供>"


def demo_typing() -> None:
    configuration: DeviceConfig = {"name": "AHU01", "timeout": 1.5}
    measurements: Measurements = {"device": "AHU01", "temperature": 24.5}
    assert type(configuration) is dict and type(measurements) is dict
    assert DeviceConfig.__closed__ is True
    assert Measurements.__extra_items__ is float

    # TypeForm 標記型別運算式，不會執行資料驗證或轉型。
    schema: TypeForm[dict[str, float]] = dict[str, float]
    assert TypeForm(schema) is schema
    assert ConfigurationBase.__disjoint_base__ is True
    assert TransportBase.__disjoint_base__ is True
    # class Invalid(ConfigurationBase, TransportBase): ...
    # 上行應由支援 PEP 800 的型別檢查器診斷，非執行期自動驗證。


def demo_json() -> None:
    snapshot = json.loads(
        '{"device":"AHU01","values":[24.5,24.8],"meta":{"ok":true}}',
        object_pairs_hook=frozendict,
        array_hook=tuple,
    )
    assert type(snapshot) is frozendict
    assert snapshot["values"] == (24.5, 24.8)
    assert type(snapshot["meta"]) is frozendict
    assert json.loads(json.dumps(snapshot))["device"] == "AHU01"


def demo_bytearray() -> None:
    buffer = bytearray(b"OK\nNEXT")
    assert buffer.take_bytes(3) == b"OK\n"
    assert buffer == bytearray(b"NEXT")
    assert buffer.take_bytes() == b"NEXT"
    assert not buffer
    expect_error(IndexError, lambda: bytearray(b"A").take_bytes(2))
    assert b"AA".replace(b"A", b"B", count=1) == b"BA"


def demo_regex() -> None:
    assert re.prefixmatch(r"AHU\d+", "AHU01/temperature").group() == "AHU01"
    assert re.prefixmatch(r"AHU\d+", "site/AHU01") is None
    assert re.search(r"AHU\d+", "site/AHU01").group() == "AHU01"
    assert re.fullmatch(r"AHU\d+", "AHU01/temperature") is None
    # match 仍然存在；3.15 是軟棄用，不是移除。
    assert re.match(r"AHU\d+", "AHU01").group() == "AHU01"


def demo_math() -> None:
    assert math.fmax(math.nan, 24.5) == 24.5
    assert math.fmin(24.5, math.nan) == 24.5
    assert math.isnan(math.fmax(math.nan, math.nan))
    assert math.isnormal(1.0) and not math.isnormal(0.0)
    assert math.issubnormal(float.fromhex("0x0.0000000000001p-1022"))
    assert math.signbit(-0.0) and not math.signbit(0.0)
    assert math.integer.gcd(12, 18) == 6
    assert math.integer.lcm(6, 8) == 24
    assert math.integer.isqrt(17) == 4
    assert math.integer.factorial(5) == 120
    assert math.integer.comb(5, 2) == 10
    assert math.integer.perm(5, 2) == 20


def demo_encoding_and_paths() -> None:
    assert sys.flags.utf8_mode in (0, 1)
    with TemporaryDirectory(prefix="python315-learning-") as folder:
        root = Path(folder)
        (root / "settings.txt").write_text("冰水閥設定", encoding="utf-8")
        assert (root / "settings.txt").read_text(encoding="utf-8") == "冰水閥設定"
        destination = root / "reports" / "daily"
        destination.mkdir(parents=True, mode=0o700, parent_mode=0o700)
        assert destination.is_dir()
    print(f"  UTF-8 mode：{sys.flags.utf8_mode}（可用 -X utf8=0 明確停用）")


def demo_base64() -> None:
    encoded = base64.b64encode(b"A", padded=False)
    assert encoded == b"QQ"
    assert base64.b64decode(encoded, padded=False) == b"A"
    assert base64.b64decode(b"QQ==", canonical=True) == b"A"


def demo_positive_literal_pattern() -> None:
    # match/case 本來就有；3.15 新增的是 literal pattern 的一元正號。
    code = 1
    match code:
        case +1:
            result = "啟用"
        case _:
            result = "其他"
    assert result == "啟用"


def demo_slots_and_slice() -> None:
    class TaggedReadings(tuple):
        __slots__ = ("device",)

    readings = TaggedReadings((24.5, 24.8))
    readings.device = "AHU01"
    assert readings.device == "AHU01" and readings[0] == 24.5
    assert slice[float].__origin__ is slice


def demo_toml_and_unicode() -> None:
    # TOML 1.1 允許 inline table 中換行及最後一個逗號。
    configuration = tomllib.loads('device = {\n name = "AHU01",\n timeout = 1.5,\n}\n')
    assert configuration["device"]["name"] == "AHU01"
    assert unicodedata.isxidstart("溫")
    assert unicodedata.isxidcontinue("7")
    assert not unicodedata.isxidstart("7")
    segments = list(unicodedata.iter_graphemes("e\u0301"))
    assert [str(segment) for segment in segments] == ["e\u0301"]
    assert (segments[0].start, segments[0].end) == (0, 2)


def demo_counter_difference() -> None:
    before = Counter(alarm=2, warning=1)
    after = Counter(alarm=1, warning=4)
    assert (before ^ after) == Counter(alarm=1, warning=3)


def demo_upgrade_breaks() -> None:
    expect_error(ValueError, lambda: datetime.strptime("02/28", "%m/%d"))
    assert datetime.strptime("2026/02/28", "%Y/%m/%d").day == 28
    expect_error(TypeError, lambda: ast.Name())
    expect_error(TypeError, lambda: ast.Constant(value=1, surplus=2))
    node = ast.Name(id="temperature", ctx=ast.Load())
    assert node.id == "temperature"


def main() -> None:
    print(sys.version)
    demos = [
        demo_lazy_import,
        demo_unpacking,
        demo_frozendict,
        demo_sentinel,
        demo_typing,
        demo_json,
        demo_bytearray,
        demo_regex,
        demo_math,
        demo_encoding_and_paths,
        demo_base64,
        demo_positive_literal_pattern,
        demo_slots_and_slice,
        demo_toml_and_unicode,
        demo_counter_difference,
        demo_upgrade_breaks,
    ]
    for demo in demos:
        demo()
        print(f"PASS {demo.__name__}")
    print(f"完成：{len(demos)} 組新特性範例均通過；靜態型別檢查不包含在此結果。")


if __name__ == "__main__":
    main()
