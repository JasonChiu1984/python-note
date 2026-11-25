"""Small standard-library CLI contract lab: plan, apply, report."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile


class InputError(Exception):
    pass


def read_object(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (ValueError, UnicodeError) as exc:
        raise InputError("設定或報告不是合法的 UTF-8 JSON") from exc
    if type(value) is not dict:
        raise InputError("JSON 最外層必須是物件")
    return value


def settings(args, env):
    fields = {"site": "demo", "limit": 10}
    src = {key: "default" for key in fields}
    if args.config:
        obj = read_object(args.config)
        if set(obj) - fields.keys():
            raise InputError("設定檔有未知欄位")
        for key, value in obj.items():
            fields[key], src[key] = value, "file"
    for key in fields:
        name = "CLI_DEMO_" + key.upper()
        if name in env:
            fields[key], src[key] = env[name], "env"
        value = getattr(args, key)
        if value is not None:
            fields[key], src[key] = value, "cli"
    if type(fields["site"]) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", fields["site"]):
        raise InputError("site 僅允許 1–32 個英數字、_ 或 -")
    limit = fields["limit"]
    if src["limit"] == "env" and isinstance(limit, str) and re.fullmatch(r"[0-9]{1,3}", limit):
        limit = int(limit)
    if type(limit) is not int or not 1 <= limit <= 500:
        raise InputError("limit 必須是 1–500 的整數")
    return {"schema_version": 1, "site": fields["site"], "limit": limit, "source": src}


def atomic_json(path, value):
    """Target and staging file share the same parent filesystem."""
    target = Path(path)
    staging = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=target.parent, prefix=".cli-report-",
                                         suffix=".tmp", delete=False) as temp:
            staging = Path(temp.name)
            json.dump(value, temp, ensure_ascii=False, allow_nan=False, sort_keys=True)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(staging, target)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def parser():
    root = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply"):
        cli = sub.add_parser(name, allow_abbrev=False)
        cli.add_argument("--config", type=Path)
        cli.add_argument("--site")
        cli.add_argument("--limit", type=int)
        if name == "apply":
            cli.add_argument("--out", type=Path, required=True)
            cli.add_argument("--dry-run", action="store_true")
    sub.add_parser("report", allow_abbrev=False).add_argument("path", type=Path)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "report":
            stored = read_object(args.path)
            if type(stored.get("schema_version")) is not int or stored["schema_version"] != 1:
                raise InputError("不支援的報告 schema")
            # Project allowlisted fields; do not echo unknown fields.
            result = {"schema_version": 1, "site": stored.get("site"), "limit": stored.get("limit")}
            if (type(result["site"]) is not str or
                    not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", result["site"]) or
                    type(result["limit"]) is not int or not 1 <= result["limit"] <= 500):
                raise InputError("報告欄位不符契約")
        else:
            result = settings(args, os.environ)
            mode = "plan"
            if args.command == "apply":
                mode = "dry-run" if args.dry_run else "apply"
                if not args.dry_run:
                    if args.config and args.out.exists() and args.config.samefile(args.out):
                        raise InputError("禁止把報告寫回輸入設定檔")
                    atomic_json(args.out, result)
            result["mode"] = mode
    except InputError as exc:
        print(f"INPUT: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        # Exception strings and arguments can contain paths or credentials.
        print(f"IO: {type(exc).__name__}", file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
