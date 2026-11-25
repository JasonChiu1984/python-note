"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('4-1', '物件比較：==（相等）與 is（同一物件）', 'from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass Point:\n    tag: str\n\na = Point("AHU1_SAT")\nb = Point("AHU1_SAT")\nalias = a\nassert a == b and a is not b and a is alias\nassert hash(a) == hash(b)\nassert {a: 240}[b] == 240\nassert {}.get("missing") is None'), ('4-2', '__str__ 與 __repr__：讓類別更善於自我表述', 'class Reading:\n    def __init__(self, tag, value):\n        self.tag, self.value = tag, value\n\n    def __str__(self):\n        return f"{self.tag}：{self.value:.1f} °C"\n\n    def __repr__(self):\n        return f"Reading(tag={self.tag!r}, value={self.value!r})"\n\nr = Reading("SAT", 24.125)\nassert f"{r!s}" == "SAT：24.1 °C"\nassert f"{r!r}" == "Reading(tag=\'SAT\', value=24.125)"\nassert repr([r]) == "[Reading(tag=\'SAT\', value=24.125)]"'), ('4-3', '定義自訂例外類別來協助除錯', 'class InvalidSample(ValueError):\n    code = "INVALID_SAMPLE"\n\ndef parse_centi_c(text):\n    try:\n        value = int(text)\n    except ValueError as err:\n        raise InvalidSample("量測值必須是整數") from err\n    if not -4000 <= value <= 10000:\n        raise InvalidSample("量測值超出工程上下限")\n    return value\n\nassert parse_centi_c("2350") == 2350\ntry:\n    parse_centi_c("bad")\nexcept InvalidSample as err:\n    assert err.code == "INVALID_SAMPLE"\n    assert isinstance(err.__cause__, ValueError)\nelse:\n    raise AssertionError("應拒絕無效量測")'), ('4-4', '複製物件：淺拷貝與深拷貝', 'from copy import copy, deepcopy\n\npoints = {"tags": ["SAT"]}\nshallow, deep = copy(points), deepcopy(points)\nassert shallow is not points and shallow["tags"] is points["tags"]\nshallow["tags"].append("RAT")\nassert points["tags"] == ["SAT", "RAT"]\nassert deep["tags"] == ["SAT"]\n\ncycle = []\ncycle.append(cycle)\nresult = deepcopy(cycle)\nassert result is not cycle and result[0] is result'), ('4-5', '抽象基礎類別（ABC）：要求子類別實作方法', 'from abc import ABC, abstractmethod\n\nclass Reader(ABC):\n    @abstractmethod\n    def read(self, tag):\n        pass\n\nclass MockReader(Reader):\n    def read(self, tag):\n        return {"SAT": 24.5}[tag]\n\nclass Incomplete(Reader):\n    pass\n\nassert MockReader().read("SAT") == 24.5\ntry:\n    Incomplete()\nexcept TypeError:\n    pass\nelse:\n    raise AssertionError("沒有實作 read 不應能建立")'), ('4-6', '物件、類別與靜態方法', 'class Equipment:\n    def __init__(self, tag):\n        self.tag = tag\n\n    def label(self):\n        return self.tag\n\n    @classmethod\n    def from_text(cls, text):\n        tag = text.strip()\n        if not cls.valid(tag):\n            raise ValueError("無效代碼")\n        return cls(tag)\n\n    @staticmethod\n    def valid(tag):\n        return bool(tag) and tag.isascii() and tag.isalnum()\n\nclass Fan(Equipment):\n    pass\n\nfan = Fan.from_text(" F01 ")\nassert isinstance(fan, Fan)\nassert fan.label() == "F01" and not Equipment.valid("")'), ('4-7', '類別變數與物件變數的陷阱', 'class AlarmBox:\n    threshold = 25\n\n    def __init__(self):\n        self.alarms = []\n\na, b = AlarmBox(), AlarmBox()\na.alarms.append("SAT-HIGH")\na.threshold = 27\nassert b.alarms == [] and a.alarms == ["SAT-HIGH"]\nassert (a.threshold, b.threshold, AlarmBox.threshold) == (27, 25, 25)'), ('4-8', '用物件實作修飾器', 'from functools import update_wrapper\n\nclass Counter:\n    def __init__(self, fn):\n        update_wrapper(self, fn)\n        self.fn = fn\n        self.calls = 0\n\n    def __call__(self, *args, **kwargs):\n        self.calls += 1\n        return self.fn(*args, **kwargs)\n\n@Counter\ndef scale(raw, *, divisor):\n    return raw / divisor\n\nassert scale(235, divisor=10) == 23.5\nassert scale.calls == 1\nassert scale.__name__ == "scale"\nassert scale.__wrapped__(420, divisor=10) == 42\nassert scale.calls == 1')]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="只跑一項，例如 2-1")
    args = parser.parse_args()
    selected = [row for row in CASES if args.case is None or row[0] == args.case]
    if not selected:
        parser.error("無此技巧編號")
    failures = 0
    for code_id, title, source in selected:
        # 各題分開解譯與工作目錄，避免全域名稱、暫存產物互相影響。
        with tempfile.TemporaryDirectory() as work:
            try:
                child = subprocess.run(
                    [sys.executable, "-I", "-X", "utf8", "-c", source],
                    cwd=work, capture_output=True, text=True, encoding="utf-8",
                    timeout=20,
                )
            except subprocess.TimeoutExpired:
                print(f"FAIL {code_id} {title}：逾時", flush=True)
                failures += 1
                continue
        print(f"{'PASS' if child.returncode == 0 else 'FAIL'} {code_id} {title}", flush=True)
        if child.returncode != 0:
            print(child.stdout + child.stderr, file=sys.stderr)
            failures += 1
    print(f"{len(selected) - failures}/{len(selected)} 通過")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
