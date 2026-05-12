from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import write_feature_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a NumPy feature matrix from CSV.")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("dist/features"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = write_feature_outputs(args.input_csv, args.out_dir)
    print(f"wrote {result.matrix_path}")
    print(f"wrote {result.stats_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
