from __future__ import annotations

from pathlib import Path
import py_compile
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def iter_python_files() -> list[Path]:
    roots = [ROOT / "src", ROOT / "tests", ROOT / "scripts"]
    return sorted(path for root in roots for path in root.rglob("*.py"))


def compile_all() -> None:
    for path in iter_python_files():
        py_compile.compile(str(path), doraise=True)


def run_unittest() -> None:
    # The CLI owns this interpreter; use only the sample's source tree.
    sys.path.insert(0, str(ROOT / "src"))
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("quality gate failed: unittest failed")
    if result.testsRun == 0:
        raise SystemExit("quality gate failed: no tests executed")
    if result.skipped or result.expectedFailures:
        raise SystemExit("quality gate failed: required tests were skipped or expected to fail")
    print(f"required tests executed successfully: {result.testsRun}")


def main() -> None:
    compile_all()
    run_unittest()
    print("quality gate passed: py_compile + unittest")


if __name__ == "__main__":
    main()
