from __future__ import annotations

import pathlib
import os
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SRC))


def run(command: list[str]) -> None:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    files = [*SRC.glob("security_engineering/*.py"), *TESTS.glob("*.py"), pathlib.Path(__file__)]
    run([sys.executable, "-m", "py_compile", *map(str, files)])
    run([sys.executable, "-m", "unittest", "discover", "-s", str(TESTS), "-v"])
    run([sys.executable, "-m", "security_engineering.demo"])
    print("security smoke passed: auth + policy + audit + manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
