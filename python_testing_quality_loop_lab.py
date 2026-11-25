"""Offline quality-loop lab. Test: python python_testing_quality_loop_lab.py --test."""
import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock


@dataclass(frozen=True)
class Reading:
    sensor: str
    celsius: float
    quality: str = "good"


def exceeds(reading: Reading, threshold: float) -> bool:
    """Only finite, valid readings can trigger; equality raises an alert."""
    return (
        reading.quality == "good"
        and math.isfinite(reading.celsius)
        and reading.celsius >= threshold
    )


def process(reading, threshold, publish):
    """Pass a publisher dependency explicitly; do not patch the global environment."""
    if not exceeds(reading, threshold):
        return False
    publish({"event": "temperature_high", **asdict(reading)})
    return True


def from_file(source, threshold, publish):
    raw = json.loads(source.read_text(encoding="utf-8"))
    return process(Reading(**raw), threshold, publish)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--threshold", type=float, default=30.0)
    args = parser.parse_args()
    if not math.isfinite(args.threshold):
        parser.error("--threshold must be finite")
    try:
        from_file(args.input, args.threshold, lambda e: print(json.dumps(e, allow_nan=False)))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"input error: {exc}\n")


class QualityLoopTests(unittest.TestCase):
    def test_rule_boundaries(self):
        cases = [
            ("below", 29.99, "good", False),
            ("equal", 30.0, "good", True),
            ("above", 30.01, "good", True),
            ("stale", 90.0, "stale", False),
            ("not-finite", float("nan"), "good", False),
        ]
        for name, value, quality, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(exceeds(Reading("T10", value, quality), 30.0), expected)

    def test_publisher_contract(self):
        publish = Mock()
        self.assertTrue(process(Reading("T10", 30.0), 30.0, publish))
        publish.assert_called_once_with({
            "event": "temperature_high", "sensor": "T10", "celsius": 30.0, "quality": "good",
        })

    def test_invalid_input_never_publishes(self):
        publish = Mock()
        self.assertFalse(process(Reading("T10", 99.0, "stale"), 30.0, publish))
        publish.assert_not_called()

    def test_utf8_integration(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "reading.json"
            source.write_text('{"sensor":"冰水","celsius":30}', encoding="utf-8")
            sent = []
            self.assertTrue(from_file(source, 30.0, sent.append))
            self.assertEqual(sent[0]["sensor"], "冰水")

    def test_cli_success_and_bad_json(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "reading.json"
            command = [sys.executable, str(Path(__file__).resolve()), str(source)]
            source.write_text('{"sensor":"T10","celsius":30}', encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["event"], "temperature_high")
            source.write_text("{broken json", encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("input error:", result.stderr)

    def test_mutant_demonstrates_missing_assertion(self):
        # The wrong '>' would still cover the equality line, but gives the wrong result.
        self.assertNotEqual(30.0 > 30.0, exceeds(Reading("T10", 30.0), 30.0))


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        unittest.main(argv=[sys.argv[0], "-v"])
    else:
        cli()
