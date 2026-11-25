"""Offline Python 3.12 examples. Run with the actual CPython 3.12 interpreter."""
import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import override


type Reading = tuple[str, float]


def first[T](items: list[T]) -> T:
    if not items:
        raise ValueError("at least one item required")
    return items[0]


def describe(item: Reading) -> str:
    name, temp = item
    record = {"zone": name, "temperature": temp}
    return f"{record["zone"]}: {record["temperature"]:.1f} °C"


def local_keys() -> set[str]:
    outer = "visible"
    return {key for item in [0] for key in locals() if key in {"outer", "item"}}


class BaseAlert:
    def classify(self, value: float) -> str:
        return "unknown"


class TemperatureAlert(BaseAlert):
    @override
    def classify(self, value: float) -> str:
        return "high" if value >= 28 else "normal"


class Checks(unittest.TestCase):
    def test_generics(self):
        self.assertEqual(first([8, 9]), 8)
        self.assertEqual(first(["AHU-01", "AHU-02"]), "AHU-01")
        self.assertEqual(Reading.__name__, "Reading")
        with self.assertRaises(ValueError):
            first([])

    def test_fstrings(self):
        self.assertEqual(describe(("AHU-01", 25.25)), "AHU-01: 25.2 °C")
        values = ["AHU-01", "AHU-02"]
        self.assertEqual(f"{'\n'.join(values)}", "AHU-01\nAHU-02")

    def test_comprehension(self):
        outer = 99
        self.assertEqual([outer * 2 for outer in range(3)], [0, 2, 4])
        self.assertEqual(outer, 99)
        self.assertEqual(local_keys(), {"outer", "item"})

    def test_override_and_raw_regex(self):
        self.assertEqual(TemperatureAlert().classify(28), "high")
        self.assertIsNotNone(re.fullmatch(r"AHU-\d{2}", "AHU-01"))

    def test_path_walk(self):
        with TemporaryDirectory() as work:
            root = Path(work)
            (root / "sample.csv").write_text("value\n25\n", encoding="utf-8")
            names = [name for _, _, files in root.walk() for name in files]
            self.assertEqual(names, ["sample.csv"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]:
        raise SystemExit("Usage: python3.12 python-312-lab.py [--test]")
    else:
        print(f"Interpreter: {sys.version.split()[0]}")
        print(describe(first([("AHU-01", 25.25), ("AHU-02", 28.5)])))
        print("Comprehension sees:", ", ".join(sorted(local_keys())))
        print("28.0 °C:", TemperatureAlert().classify(28.0))
