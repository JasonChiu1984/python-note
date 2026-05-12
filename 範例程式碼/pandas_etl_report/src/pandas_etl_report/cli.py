from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Pandas revenue report from orders CSV.")
    parser.add_argument("orders_csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("dist/orders-report.json"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output = write_report(args.orders_csv, args.out)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
