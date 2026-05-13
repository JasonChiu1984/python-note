from __future__ import annotations

import os
from pathlib import Path
import py_compile
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def iter_python_files() -> list[Path]:
    roots = [ROOT / "src", ROOT / "tests", ROOT / "scripts"]
    return sorted(path for root in roots for path in root.rglob("*.py"))


def compile_all() -> None:
    for path in iter_python_files():
        py_compile.compile(str(path), doraise=True)


def run_unittest() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        cwd=ROOT,
        env=env,
        check=True,
    )


def main() -> None:
    compile_all()
    run_unittest()
    print("quality gate passed: py_compile + unittest")


if __name__ == "__main__":
    main()
