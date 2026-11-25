"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('6-1', '寫出符合 Python 風格的 for 迴圈', 'def format_points(names: list[str], values: list[float]) -> list[str]:\n    rows = []\n    pairs = zip(names, values, strict=True)\n    for number, (name, value) in enumerate(pairs, start=1):\n        rows.append(f"{number}. {name}: {value:.1f} °C")\n    return rows\n\nassert format_points(["送風", "回風"], [18.25, 24.1]) == [\n    "1. 送風: 18.2 °C",\n    "2. 回風: 24.1 °C",\n]\nassert format_points([], []) == []\nfor names, values in [(["送風"], []), ([], [18.0])]:\n    try:\n        format_points(names, values)\n    except ValueError:\n        pass\n    else:\n        raise AssertionError("點位與讀值長度不符，應回報錯誤")\n'), ('6-2', '生成式：Comprehension', 'readings = [("AHU-1", "ok", 18.0), ("AHU-2", "bad", 80.0),\n            ("AHU-3", "ok", 23.0)]\nname = "外層變數"\n\naccepted = [\n    (name, round(value * 9 / 5 + 32, 1))\n    for name, quality, value in readings\n    if quality == "ok"\n]\nquality_codes = {quality for _, quality, _ in readings}\nby_point = {name: value for name, value in accepted}\n\nassert accepted == [("AHU-1", 64.4), ("AHU-3", 73.4)]\nassert quality_codes == {"ok", "bad"}\nassert by_point == {"AHU-1": 64.4, "AHU-3": 73.4}\nassert name == "外層變數"\nassert {key: v for key, v in [("A", 1), ("A", 2)]} == {"A": 2}\nmatrix = [[1, 2], [], [3]]\nassert [v for row in matrix for v in row] == [1, 2, 3]\n'), ('6-3', 'List 切片：所謂「壽司算符」其實是 slice', 'samples = [10, 20, 30, 40, 50]\nassert samples[1:4:2] == [20, 40]\nassert samples[-3:] == [30, 40, 50]\nassert samples[-1::-1] == [50, 40, 30, 20, 10]\nassert samples[-1:-1:-1] == []\nassert samples[99:] == []\nselection = slice(1, 4, 2)\nassert samples[selection] == [20, 40]\n\nchanged = samples[:]\nchanged[1:3] = [88]\nassert changed == [10, 88, 40, 50] and samples[1] == 20\nchanged[::2] = [100, 400]\nassert changed == [100, 88, 400, 50]\n\nnested = [["送風"], ["回風"]]\ncopied = nested[:]\ncopied.append(["新風"])\ncopied[0].append("備援")\nassert len(nested) == 2 and nested[0] == ["送風", "備援"]\n'), ('6-4', 'Iterator：掌握走訪器協定', 'class Countdown:\n    def __init__(self, start: int):\n        self.current = start\n\n    def __iter__(self):\n        return self\n\n    def __next__(self) -> int:\n        if self.current <= 0:\n            raise StopIteration\n        value = self.current\n        self.current -= 1\n        return value\n\ncountdown = Countdown(3)\nassert iter(countdown) is countdown\nassert next(countdown) == 3\nassert list(countdown) == [2, 1]\nassert list(countdown) == []\nend = object()\nassert next(countdown, end) is end\n\ndata = [None, 21]\na, b = iter(data), iter(data)\nassert next(a, end) is None and next(b, end) is None\nassert list(a) == [21] and list(b) == [21]\n'), ('6-5', '產生器函式：以 yield 暫停後再繼續', 'from collections.abc import Generator\nfrom contextlib import closing\n\ntrace: list[str] = []\n\ndef good_values(rows: list[tuple[str, float]]) -> Generator[float, None, None]:\n    trace.append("開始")\n    try:\n        for state, value in rows:\n            trace.append(f"處理 {value:g}")\n            if state == "ok":\n                yield value\n    finally:\n        trace.append("清理")\n\nrecords = [("bad", 99.0), ("ok", 18.0), ("ok", 20.0)]\nstream = good_values(records)\nassert trace == []\nwith closing(stream) as values:\n    assert next(values) == 18.0\n    assert trace == ["開始", "處理 99", "處理 18"]\nassert trace[-1] == "清理" and "處理 20" not in trace\nassert list(stream) == []\nassert list(good_values([])) == []\n'), ('6-6', '產生器運算式：把延遲求值寫成一個表達式', 'from itertools import islice\n\ntrace: list[str] = []\n\ndef source():\n    trace.append("建立來源")\n\n    def rows():\n        for value in [12, 20, 26, 28]:\n            trace.append(f"讀取 {value}")\n            yield value\n\n    return rows()\n\nalarms = (value - 18 for value in source() if value > 18)\nassert trace == ["建立來源"]\nassert list(islice(alarms, 2)) == [2, 8]\nassert trace == ["建立來源", "讀取 12", "讀取 20", "讀取 26"]\nassert list(alarms) == [10]\nassert list(alarms) == []\n\nthreshold = 15\nlazy_filter = (v for v in [16, 20] if v > threshold)\nthreshold = 17\nassert list(lazy_filter) == [20]  # 過濾條件是在走訪時執行\n'), ('6-7', '走訪器串聯：串接來源，再分層轉換', 'from collections.abc import Iterable, Iterator\nfrom itertools import chain\n\ndef good_temperatures(\n    batches: Iterable[Iterable[tuple[str, int]]],\n) -> Iterator[float]:\n    merged = chain.from_iterable(batches)\n    return (decic / 10 for status, decic in merged if status == "ok")\n\nseen: list[str] = []\n\ndef batches():\n    seen.append("批次 A")\n    yield [("bad", 999), ("ok", 215)]\n    seen.append("批次 B")\n    yield []\n    seen.append("批次 C")\n    yield [("ok", 223), ("ok", 240)]\n\nstream = good_temperatures(batches())\nassert seen == []\nassert next(stream) == 21.5 and seen == ["批次 A"]\nassert next(stream) == 22.3 and seen == ["批次 A", "批次 B", "批次 C"]\nassert list(stream) == [24.0]\nassert list(good_temperatures([])) == []\n'), ('6-8', 'itertools：組合有限與無限走訪器', 'from itertools import accumulate, count, groupby, islice, pairwise\n\nseq = list(islice(count(start=100, step=2), 4))\nassert seq == [100, 102, 104, 106]\nassert list(islice(count(), 0)) == []\n\nreadings = [18, 22, 21, 25]\ndeltas = [curr - prev for prev, curr in pairwise(readings)]\nassert deltas == [4, -1, 4]\nassert list(pairwise([99])) == []\nassert list(accumulate(deltas, initial=0)) == [0, 4, 3, 7]\n\nevents = [("ok", 1), ("ok", 2), ("warn", 3), ("ok", 4)]\nruns = [(key, [seq for _, seq in group])\n        for key, group in groupby(events, key=lambda row: row[0])]\nassert runs == [("ok", [1, 2]), ("warn", [3]), ("ok", [4])]\n')]

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
