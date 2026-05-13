from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    py_files = [str(path) for path in SRC.rglob("*.py")]
    py_files += [str(path) for path in TESTS.rglob("*.py")]
    py_files.append(str(pathlib.Path(__file__).resolve()))
    run([sys.executable, "-m", "py_compile", *py_files])
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(TESTS), "-v"], cwd=ROOT, env=env, check=True)
    output = subprocess.check_output(
        [sys.executable, "-m", "observability_operations.demo"],
        cwd=ROOT,
        env=env,
        text=True,
    )
    payload = json.loads(output)
    assert payload["metrics"]["requests_total"] == 2
    assert payload["health"]["live"] == "ok"
    assert "slo" in payload
    print("observability smoke passed: logs + metrics + health + SLO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
