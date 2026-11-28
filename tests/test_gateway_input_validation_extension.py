import json
import runpy
from pathlib import Path

import pytest

demo = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                          "extensions/python_information_security_tutorial/example.py"))


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("point", None, "點位型別錯誤"),
    ("nonce", None, "nonce 型別錯誤"),
    ("ts", True, "時間戳必須是整數秒"),
    ("value", False, "需要有限數值"),
    ("value", float("inf"), "需要有限數值"),
    ("sig", None, "簽章格式錯誤"),
])
def test_invalid_telemetry_is_rejected_without_updating_state(field, value, reason):
    v = demo["Validator"]()
    now = demo["NOW"]
    first = demo["make"]("AHU1_SAT", 18.2, now - 60, "a1")
    assert v.check(first) == "接受"
    good = demo["make"]("AHU1_SAT", 18.5, now, "a2")
    untyped = json.loads(good)
    untyped[field] = value
    assert reason in v.check(json.dumps(untyped).encode())
    assert v.last == {"AHU1_SAT": (now - 60, 18.2)}
    assert v.seen_nonce == {"a1"}
    assert v.check(good) == "接受"


def test_json_array_is_not_an_event_object():
    assert demo["Validator"]().check(b"[]") == "拒絕：事件欄位不符"
