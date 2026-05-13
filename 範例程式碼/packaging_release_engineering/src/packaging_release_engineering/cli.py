from __future__ import annotations

import argparse
from pathlib import Path

from .release import ReleaseGateError, run_release_gate, validate_release_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run packaging release gate checks.")
    parser.add_argument("command", choices=["verify", "build"], help="verify metadata or build release evidence")
    parser.add_argument("--project-root", default=".", help="project root path")
    parser.add_argument("--dist-dir", default=None, help="optional dist output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    dist_dir = Path(args.dist_dir).resolve() if args.dist_dir else None

    try:
        if args.command == "verify":
            metadata = validate_release_metadata(project_root)
            print(f"release metadata ok: {metadata.name} {metadata.version}")
            return 0
        archive_path, manifest_path = run_release_gate(project_root, dist_dir=dist_dir)
        print(f"release artifact: {archive_path}")
        print(f"release manifest: {manifest_path}")
        return 0
    except ReleaseGateError as exc:
        parser.exit(status=2, message=f"release gate failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
