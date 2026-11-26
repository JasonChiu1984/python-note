"""Offline roadmap lab: parse → plan → publish. Python 3.11+, standard library."""
import argparse
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
import unittest


@dataclass(frozen=True, slots=True)
class Reading:
    point_id: str
    temperature: Decimal


def parse_reading(line: str) -> Reading:
    """Parse one teaching row; input uses explicit decimal and degree Celsius."""
    columns = [s.strip() for s in line.split(",")]
    if len(columns) != 2:
        raise ValueError("expected point_id,temperature_c")
    point_id, raw = columns
    if not re.fullmatch(r"[A-Z][A-Z0-9_-]{0,23}", point_id):
        raise ValueError("invalid point identifier")
    if not re.fullmatch(r"[+-]?[0-9]{1,3}(?:\.[0-9]{1,2})?", raw):
        raise ValueError("temperature must be a decimal with at most two fractional places")
    value = Decimal(raw)
    if not Decimal("-40") <= value <= Decimal("85"):
        raise ValueError("temperature outside this lesson's accepted range")
    return Reading(point_id, abs(value) if not value else value)


@dataclass(frozen=True, slots=True)
class Plan:
    rows: tuple[Reading, ...]
    duplicated: int

    def artifact(self) -> bytes:
        rows = [{"point_id": x.point_id, "temperature_c": format(x.temperature, ".2f")}
                for x in self.rows]
        return (json.dumps({"schema": 1, "rows": rows},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def plan(lines) -> Plan:
    accepted = {}
    duplicated = 0
    for n, line in enumerate(lines, 1):
        try:
            reading = parse_reading(line)
            existing = accepted.get(reading.point_id)
            if existing and existing != reading:
                raise ValueError(f"conflicting value for {reading.point_id}")
            if existing:
                duplicated += 1
            else:
                accepted[reading.point_id] = reading
        except ValueError as exc:
            raise ValueError(f"row {n}: {exc}") from exc
    if not accepted:
        raise ValueError("empty input is not a valid snapshot")
    return Plan(tuple(accepted[k] for k in sorted(accepted)), duplicated)


def publish_snapshot(path: Path, artifact: bytes) -> None:
    """Same-directory replace; one writer, existing authorized output directory."""
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".snapshot-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(artifact)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


DEMO = ("AHU-B,24.8", "AHU-A,25.50", "AHU-A,25.5")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("parse", "plan", "publish"))
    parser.add_argument("--output", type=Path, help="local output path, only for publish")
    parser.add_argument("--apply", action="store_true", help="actually replace local output")
    args = parser.parse_args(argv)
    if args.mode != "publish" and (args.output or args.apply):
        parser.error("output and apply are only valid for publish")
    if args.mode == "publish" and args.apply and not args.output:
        parser.error("--apply requires --output")
    if args.mode == "parse":
        print(parse_reading(DEMO[1]))
        return 0
    job = plan(DEMO)
    artifact = job.artifact()
    if args.mode == "plan":
        print(artifact.decode(), end="")
    elif args.apply:
        try:
            publish_snapshot(args.output, artifact)
        except OSError as exc:
            print(f"write failed: {exc}", file=sys.stderr)
            return 1
    print(f"accepted={len(job.rows)} duplicated={job.duplicated} digest={sha256(artifact).hexdigest()} "
          f"written={'yes' if args.apply else 'no'}", file=sys.stderr)
    return 0


class TestRoadmapCore(unittest.TestCase):
    def test_decimal_and_identity(self):
        a, b = parse_reading("AHU-A,25.5"), parse_reading("AHU-A,25.50")
        self.assertEqual(a, b)
        self.assertIsNot(a, b)

    def test_invalid(self):
        for row in ("AHU-A,NaN", "AHU-A,86", "bad,25", "AHU-A,25,24"):
            with self.subTest(value=row), self.assertRaises(ValueError):
                parse_reading(row)

    def test_plan_reproducible(self):
        self.assertEqual(plan(DEMO).artifact(), plan(reversed(DEMO)).artifact())
        self.assertEqual(plan(DEMO).duplicated, 1)
        with self.assertRaisesRegex(ValueError, "conflicting value"):
            plan(("AHU-A,25", "AHU-A,26"))
        with self.assertRaisesRegex(ValueError, "empty input"):
            plan([])

    def test_signed_zero_order_independent(self):
        rows = ("AHU-A,-0.00", "AHU-A,0.0")
        self.assertEqual(plan(rows).artifact(), plan(reversed(rows)).artifact())

    def test_cli_preview_and_apply(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text("prior\n")
            self.assertEqual(main(["publish", "--output", str(path)]), 0)
            self.assertEqual(path.read_text(), "prior\n")
            self.assertEqual(main(["publish", "--apply", "--output", str(path)]), 0)
            self.assertEqual(path.read_bytes(), plan(DEMO).artifact())
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_failed_replace_cleans_temporary_and_preserves_target(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            sentinel = target / "old"
            sentinel.write_text("prior")
            with self.assertRaises(OSError):
                publish_snapshot(target, b"invalid target")
            self.assertEqual(sentinel.read_text(), "prior")
            self.assertEqual(list(Path(directory).iterdir()), [target])


if __name__ == "__main__":
    raise SystemExit(main())
