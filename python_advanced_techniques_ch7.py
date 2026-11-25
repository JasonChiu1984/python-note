"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('7-1', '找不到鍵時，選對 dict 的預設值', 'from collections import defaultdict\n\nsettings = {"period": 0, "source": None}\nmissing = object()\nassert settings.get("period", 10) == 0\nassert settings.get("source", missing) is None\nassert settings.get("timeout", missing) is missing\nassert settings.get("timeout", 5) == 5 and "timeout" not in settings\n\ngroups = {}\ngroups.setdefault("AHU", []).append("T01")\ngroups.setdefault("CH", []).append("T02")\nassert groups == {"AHU": ["T01"], "CH": ["T02"]}\n\nlazy = defaultdict(list)\nassert lazy.get("CH") is None and "CH" not in lazy\nlazy["CH"].append("T03")\nassert lazy["CH"] == ["T03"]\n'), ('7-2', '按鍵、值或複合條件排序 dict', 'priority = {"AHU-B": 5, "AHU-C": 2, "AHU-A": 5}\nassert sorted(priority) == ["AHU-A", "AHU-B", "AHU-C"]\n\n# 重要程度遞減；同分用設備名稱遞增。\nranked = sorted(priority.items(), key=lambda pair: (-pair[1], pair[0]))\nassert ranked == [("AHU-A", 5), ("AHU-B", 5), ("AHU-C", 2)]\nassert list(dict(ranked)) == ["AHU-A", "AHU-B", "AHU-C"]\nassert list(priority) == ["AHU-B", "AHU-C", "AHU-A"]\n'), ('7-3', '用 dict 分派固定命令（模擬 switch）', 'def brief(readings):\n    return f"{len(readings)} 筆"\n\ndef detail(readings):\n    return ", ".join(str(value) for value in readings)\n\nHANDLERS = {"brief": brief, "detail": detail}\n\ndef run(command, readings):\n    handler = HANDLERS.get(command.strip().lower())\n    if handler is None:\n        raise ValueError("不支援的命令")\n    return handler(readings)\n\nassert run(" Brief ", [18, 20]) == "2 筆"\nassert run("detail", [18, 20]) == "18, 20"\ntry:\n    run("delete", [18, 20])\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError("未知命令本應被拒絕")\n'), ('7-4', '更新字典鍵值時，避開迭代與共用物件陷阱', 'from copy import deepcopy\n\nraw = {"T01": {"enabled": True}, "legacy": {"enabled": False}}\nfiltered = {k: v for k, v in raw.items() if v["enabled"]}\nassert set(filtered) == {"T01"}\nassert filtered["T01"] is raw["T01"]  # 重建外層仍不複製內層\n\nedited = deepcopy(filtered)\nedited["T01"]["enabled"] = False\nassert raw["T01"]["enabled"] is True\n\nids = {"old": 1, "keep": 2}\nfor key, value in list(ids.items()):\n    if key == "old":\n        if "new" in ids:\n            raise ValueError("改名會覆蓋既有鍵")\n        ids["new"] = ids.pop(key)\nassert ids == {"keep": 2, "new": 1}\n'), ('7-5', '合併 dict：右邊優先不是遞迴合併', 'defaults = {"period_s": 5, "serial": {"baud": 9600, "parity": "N"}}\noverride = {"period_s": 2, "serial": {"baud": 19200}}\n\nshallow = defaults | override\nassert shallow["serial"] == {"baud": 19200}\nmerged = shallow | {"serial": defaults["serial"] | override["serial"]}\nassert merged["serial"] == {"baud": 19200, "parity": "N"}\nassert defaults["period_s"] == 5 and defaults["serial"]["baud"] == 9600\n\noriginal = {"a": 1}\nassert original.update({"a": 2}) is None\nassert original == {"a": 2}\n'), ('7-6', '依輸出用途美觀呈現 dict', 'import json\nfrom pprint import pformat\n\nreport = {"設備": "AHU-01", "量測": {"溫度": 23.5, "有效": True}}\ndisplay = pformat(report, width=24, sort_dicts=False)\npayload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)\nassert "設備" in display and "設備" in payload\nassert json.loads(payload) == report\nprint(display)\nprint(payload)\n')]

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
