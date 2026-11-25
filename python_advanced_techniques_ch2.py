"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('2-1', 'assert：檢查內部不變條件', 'def window(start: int, end: int) -> tuple[int, int]:\n    if end < start:\n        raise ValueError("end must not precede start")\n    span = end - start\n    assert span >= 0, "window length invariant"\n    return start, span\n\nassert window(3, 8) == (3, 5)\ntry:\n    window(8, 3)\nexcept ValueError:\n    pass\nelse:\n    raise RuntimeError("invalid input was accepted")\n'), ('2-2', '容器逗號：尾逗號、單項 tuple 與字串串接', 'channels = [\n    "supply",\n    "return",\n]\nsingle = ("supply",)\ngrouped = ("supply")\naccidental = [\n    "supply"\n    "return",\n]\nassert channels == ["supply", "return"]\nassert isinstance(single, tuple) and isinstance(grouped, str)\nassert accidental == ["supplyreturn"]\n'), ('2-3', 'with：用 context manager 管理資源', 'from io import StringIO\n\nclass Buffer:\n    def __enter__(self):\n        self.stream = StringIO()\n        return self.stream\n\n    def __exit__(self, exc_type, exc, traceback):\n        self.stream.close()\n        return False\n\ntry:\n    with Buffer() as stream:\n        stream.write("CHW01")\n        raise ValueError("invalid sample")\nexcept ValueError as exc:\n    assert str(exc) == "invalid sample"\nelse:\n    raise RuntimeError("exception was suppressed")\nassert stream.closed\n'), ('2-4', '底線命名：約定、名稱改寫與特殊名稱', 'class Base:\n    def __init__(self):\n        self.__rate = 6\n\n    def base_rate(self):\n        return self.__rate\n\nclass Pump(Base):\n    def __init__(self):\n        super().__init__()\n        self.__rate = 9\n\n    def pump_rate(self):\n        return self.__rate\n\npump = Pump()\nassert (pump.base_rate(), pump.pump_rate()) == (6, 9)\nassert pump._Base__rate == 6  # demonstrates that it is not private access\n'), ('2-5', '四種字串格式化：依使用邊界選工具', 'from string import Template\n\ndevice, value = "CHW01", 7.25\na = "%s %.2f" % (device, value)\nb = "{} {:.2f}".format(device, value)\nc = f"{device} {value:.2f}"\nd = Template("$device $value").substitute(device=device, value=f"{value:.2f}")\nassert a == b == c == d == "CHW01 7.25"\n'), ('2-6', '指派運算式 :=：在條件中保存結果', 'def parse(raw: str) -> int | None:\n    try:\n        return int(raw)\n    except ValueError:\n        return None\n\nvalues = []\nfor raw in ["0", "bad", "12"]:\n    if (value := parse(raw)) is not None:\n        values.append(value)\nassert values == [0, 12]\n'), ('2-7', 'Python 之禪：把設計取捨落到可驗證行為', 'def classify(flow: int | None) -> str:\n    if flow is None:\n        return "missing"\n    if flow == 0:\n        return "stopped"\n    return "running"\n\nassert [classify(x) for x in (None, 0, 35)] == [\n    "missing", "stopped", "running",\n]\n'), ('naming', 'Python 命名規則：識別字、長度與格式', 'import keyword\nimport unicodedata\n\n\ndef valid_identifier(text: str, *, ascii_only: bool = False) -> bool:\n    """語法驗證加上可選的 ASCII 專案規範；不把軟關鍵字當禁字。"""\n    return (\n        text.isidentifier()\n        and not keyword.iskeyword(text)\n        and (not ascii_only or text.isascii())\n    )\n\n\nclass Base:\n    def __init__(self) -> None:\n        self.__cache = {"SAT": 22.0}\n\n\nassert "class".isidentifier() and not valid_identifier("class")\nassert valid_identifier("class_") and not valid_identifier("bad-name")\nassert not valid_identifier("2nd_floor") and valid_identifier("floor_2")\nassert keyword.issoftkeyword("match") and valid_identifier("match")\nassert valid_identifier("送風溫度") and not valid_identifier("送風溫度", ascii_only=True)\nassert valid_identifier("measurement_" + "x" * 300)  # 行長規範不是識別字限制\nassert unicodedata.normalize("NFKC", "K") == "K"\nassert len({"K": 1, "K": 2}) == 2  # 字典字串鍵不經識別字正規化\nassert vars(Base())["_Base__cache"] == {"SAT": 22.0}  # 改寫不是私有阻擋\n')]

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
