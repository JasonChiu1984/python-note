"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('3-1', '函式是一級物件：傳遞策略與回呼', 'def scale_by(factor):\n    def scale(value):\n        return value * factor\n    return scale\n\ndef convert(values, transform):\n    return [transform(value) for value in values]\n\nstrategies = {"raw": scale_by(1), "tenths": scale_by(0.1)}\nassert convert([70, 80], strategies["raw"]) == [70, 80]\nassert convert([70, 80], strategies["tenths"]) == [7.0, 8.0]\n'), ('3-2', 'lambda：短小且只包含一個運算式', 'readings = [("B", 8), ("A", 8), ("C", 7)]\nranked = sorted(readings, key=lambda row: (-row[1], row[0]))\nassert ranked == [("A", 8), ("B", 8), ("C", 7)]\nassert readings[0] == ("B", 8)\n'), ('3-3', '修飾器：保留原呼叫契約，抽出橫切責任', 'from functools import wraps\n\nevents = []\n\ndef observe(fn):\n    @wraps(fn)\n    def wrapper(*args, **kwargs):\n        try:\n            return fn(*args, **kwargs)\n        finally:\n            events.append(fn.__name__)\n    return wrapper\n\n@observe\ndef read(value):\n    if value is None:\n        raise ValueError("missing")\n    return value\n\nassert read(7) == 7 and read.__name__ == "read"\ntry:\n    read(None)\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError("wrapper suppressed error")\nassert events == ["read", "read"]\n'), ('3-4', '*args 與 **kwargs：接收額外呼叫引數', 'def format_batch(site, *points, precision=1, **labels):\n    return site, points, precision, labels\n\nsample = format_batch("Plant01", "supply", "return", precision=2, unit="C")\nassert sample == ("Plant01", ("supply", "return"), 2, {"unit": "C"})\nassert format_batch("Plant02") == ("Plant02", (), 1, {})\n'), ('3-5', '引數解包：在呼叫端展開 iterable 與 mapping', 'def delta(supply, return_water, *, decimals):\n    return round(return_water - supply, decimals)\n\nsamples = [7.0, 12.25]\noptions = {"decimals": 2}\nassert delta(*samples, **options) == 5.25\ntry:\n    delta(*samples, **options, **{"decimals": 1})\nexcept TypeError:\n    pass\nelse:\n    raise AssertionError("duplicate keyword did not fail")\n'), ('3-6', '隱含 return：None 不是失敗或數字零', 'def read(data: dict[str, int], key: str) -> int | None:\n    if key in data:\n        return data[key]\n    return None\n\ndef append_log(entries: list[str], event: str) -> None:\n    entries.append(event)\n\nevents = []\nassert append_log(events, "ready") is None\nassert events == ["ready"]\nassert read({"flow": 0}, "flow") == 0\nassert read({"flow": 0}, "pressure") is None\n'), ('3-7', '位置限定 / 與關鍵字限定 *', 'def report(device, /, value, *, unit):\n    return f"{device} {value} {unit}"\n\nassert report("CHW01", value=7, unit="C") == "CHW01 7 C"\nfor invalid in (\n    lambda: report(device="CHW01", value=7, unit="C"),\n    lambda: report("CHW01", 7, "C"),\n):\n    try:\n        invalid()\n    except TypeError:\n        pass\n    else:\n        raise AssertionError("invalid calling convention was accepted")\n')]

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
