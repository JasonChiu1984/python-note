"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('5-1', '各種 Python 字典', 'from collections import ChainMap, defaultdict\n\ndefaults = {"poll_s": 5, "timeout_s": 2}\nhvac = {"poll_s": 1}\nsettings = ChainMap(hvac, defaults)\nassert (settings["poll_s"], settings["timeout_s"]) == (1, 2)\nsettings["timeout_s"] = 3\nassert (hvac["timeout_s"], defaults["timeout_s"]) == (3, 2)\n\npoints = defaultdict(list)\nassert points.get("AHU02") is None and "AHU02" not in points\npoints["AHU01"].append("SAT")\npoints["AHU02"].append("RAT")\nassert dict(points) == {"AHU01": ["SAT"], "AHU02": ["RAT"]}\n'), ('5-2', '各種 Python 陣列', 'from array import array\nimport struct\n\nvalues = array("H", [400, 500])\nassert list(values) == [400, 500]\nwire = struct.pack("!2H", *values)\nassert wire.hex() == "019001f4"\nassert struct.unpack("!2H", wire) == (400, 500)\n\neditable = bytearray(wire)\nwith memoryview(editable) as view:\n    view[0] = 0\nassert editable.hex() == "009001f4"\neditable.append(0)\nassert len(editable) == 5\n'), ('5-3', '各種儲存記錄用的資料結構', 'from dataclasses import dataclass\nfrom typing import NamedTuple, TypedDict\n\nclass ReadingInput(TypedDict):\n    point: str\n    value_c: float\n\nclass PointKey(NamedTuple):\n    unit: str\n    point: str\n\n@dataclass(frozen=True, slots=True)\nclass Reading:\n    key: PointKey\n    value_c: float\n\nraw: ReadingInput = {"point": "SAT", "value_c": 22.0}\nmeasurement = Reading(PointKey("AHU01", raw["point"]), raw["value_c"])\nassert (measurement.key.unit, measurement.value_c) == ("AHU01", 22.0)\nassert tuple(measurement.key) == ("AHU01", "SAT")\n'), ('5-4', 'set（集合）與多重集合', 'from collections import Counter\n\nexpected = {"SAT", "RAT"}\nreceived = ["SAT", "SAT", "OAT"]\nassert expected - set(received) == {"RAT"}\ncounts = Counter(received)\nassert counts["SAT"] == 2 and counts["RAT"] == 0\ndelta = Counter({"SAT": 1, "RAT": 1})\ndelta.subtract(counts)\nassert delta["SAT"] == -1 and delta["RAT"] == 1\nassert set(+delta) == {"RAT"}  # 單元正號去除零與負計數\n'), ('5-5', '堆疊（stack，LIFO）', 'def balanced(text: str) -> bool:\n    expected = {"(": ")", "[": "]", "{": "}"}\n    stack = []\n    for ch in text:\n        if ch in expected:\n            stack.append(expected[ch])\n        elif ch in expected.values():\n            if not stack or stack.pop() != ch:\n                return False\n    return not stack\n\nassert balanced("function([1, {2}])")\nassert not balanced("([)]")\nassert not balanced("(missing")\nassert not balanced("]")\n'), ('5-6', '佇列（queue，FIFO）', 'from collections import deque\nfrom queue import Full, Queue\n\npending = deque(["AHU01", "AHU02"])\nassert pending.popleft() == "AHU01"\nassert pending.popleft() == "AHU02"\n\nchannel: Queue[str] = Queue(maxsize=1)\nchannel.put_nowait("讀取 SAT")\ntry:\n    channel.put_nowait("讀取 RAT")\nexcept Full:\n    pass                         # 真實系統應依契約重試、限流或回報\nelse:\n    raise AssertionError("應觸發背壓")\njob = channel.get_nowait()\ntry:\n    assert job == "讀取 SAT"\nfinally:\n    channel.task_done()\nchannel.join()\n'), ('5-7', '優先佇列（priority queue）', 'from heapq import heappop, heappush\nfrom itertools import count\n\njobs = []\nserial = count()\nfor rank, name in [(20, "例行巡檢"), (5, "先到告警"), (5, "後到告警")]:\n    heappush(jobs, (rank, next(serial), {"name": name}))\n\nassert jobs[0][0] == 5\nordered = [heappop(jobs)[2]["name"] for _ in range(len(jobs))]\nassert ordered == ["先到告警", "後到告警", "例行巡檢"]\n')]

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
