"""CLI 契約：argparse 子命令、--dry-run 預設、結束碼語意、機器可讀的 JSON 摘要（標準函式庫）。"""
import argparse
import json
import sys

EXIT_OK, EXIT_PARTIAL, EXIT_USAGE, EXIT_FAILED = 0, 1, 2, 3


def build_parser():
    p = argparse.ArgumentParser(prog="bmsctl", description="批次設定點工具")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set", help="設定冰機出水溫度")
    s.add_argument("devices", nargs="+")
    s.add_argument("--value", type=float, required=True)
    s.add_argument("--apply", action="store_true", help="實際寫入；預設只模擬")
    s.add_argument("--json", action="store_true", help="輸出 JSON 摘要")
    return p


def run(argv, offline=("CH-03",)):
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        return EXIT_USAGE if e.code else EXIT_OK, None
    if not 5.0 <= args.value <= 15.0:
        return EXIT_USAGE, {"error": f"value {args.value} 超出 5–15"}
    done, failed = [], []
    for d in args.devices:
        (failed if d in offline else done).append(d)
    summary = {"mode": "apply" if args.apply else "dry-run", "value": args.value, "ok": done, "failed": failed}
    code = EXIT_OK if not failed else (EXIT_PARTIAL if done else EXIT_FAILED)
    return code, summary


if __name__ == "__main__":
    sys.stderr = sys.stdout                          # 讓 argparse 的錯誤訊息也出現在範例輸出
    for argv in (["set", "CH-01", "CH-02", "--value", "7.5"],
                 ["set", "CH-01", "CH-03", "--value", "7.5", "--apply", "--json"],
                 ["set", "CH-03", "--value", "7.5", "--apply"],
                 ["set", "CH-01", "--value", "20"],
                 ["set", "CH-01"]):
        code, summary = run(argv)
        print(f"$ bmsctl {' '.join(argv)}\n  結束碼 {code}；{json.dumps(summary, ensure_ascii=False) if summary else ''}")
