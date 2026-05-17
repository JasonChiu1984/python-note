from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .engine import (
    EXIT_PARTIAL,
    EXIT_SUCCESS,
    EXIT_VALIDATION,
    apply_manifest,
    build_summary_line,
    load_manifest,
    plan_manifest,
    write_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI automation engineering sample")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="validate manifest and preview changes")
    plan.add_argument("--manifest", required=True)
    plan.add_argument("--output", required=True)

    apply_cmd = subparsers.add_parser("apply", help="execute manifest")
    apply_cmd.add_argument("--manifest", required=True)
    apply_cmd.add_argument("--output", required=True)
    apply_cmd.add_argument("--dry-run", action="store_true")

    report = subparsers.add_parser("report", help="print existing report summary")
    report.add_argument("--input", required=True)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            print(
                "mode={mode} dry_run={dry_run} validated={validated} blocked={blocked} executed={executed} status={status}".format(
                    **payload
                )
            )
            return EXIT_SUCCESS

        items = load_manifest(Path(args.manifest))
        if args.command == "plan":
            report = plan_manifest(items)
        else:
            report = apply_manifest(items, dry_run=bool(getattr(args, "dry_run", False)))
        write_report(report, Path(args.output))
        print(build_summary_line(report))
        return EXIT_SUCCESS if report.status == "success" else EXIT_PARTIAL
    except ValueError as exc:
        print(f"validation_error: {exc}")
        return EXIT_VALIDATION


if __name__ == "__main__":
    raise SystemExit(run())
