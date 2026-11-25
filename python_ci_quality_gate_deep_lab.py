"""離線品質閘門：Python 3.11+；只操作暫存合成資料，不發版、不部署。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

FIXTURE = b'{"schema":1,"sample":"quality-gate"}\n'
EXPECTED_SHA256 = hashlib.sha256(FIXTURE).hexdigest()


def sha256_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_gate(*, inject="none", timeout=5):
    report = {"schema": 1, "python": sys.version.split()[0],
              "mode": "offline-synthetic", "stages": []}
    stages = report["stages"]
    t = time.monotonic()
    try:
        child = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve()), "--fixture-tests",
             *(["--inject", "tests"] if inject == "tests" else [])],
            shell=False, capture_output=True, text=True, timeout=timeout, check=False
        )
        ok = child.returncode == 0
        stages.append({"name": "test", "status": "pass" if ok else "fail",
                       "child_exit": child.returncode,
                       "elapsed_ms": round((time.monotonic()-t)*1000)})
    except subprocess.TimeoutExpired:
        ok = False
        stages.append({"name": "test", "status": "fail", "reason": "timeout",
                       "elapsed_ms": round((time.monotonic()-t)*1000)})
    if not ok:
        stages.append({"name": "artifact", "status": "skip"})
        return report, 1
    with tempfile.TemporaryDirectory(prefix="quality-gate-") as path:
        artifact = Path(path) / "artifact.json"
        artifact.write_bytes(FIXTURE + (b"tampered" if inject == "artifact" else b""))
        actual = sha256_file(artifact)
    ok = actual == EXPECTED_SHA256
    stages.append({"name": "artifact", "status": "pass" if ok else "fail",
                   "expected_sha256": EXPECTED_SHA256, "actual_sha256": actual})
    return report, 0 if ok else 1


def fixture_tests(fail=False):
    class Example(unittest.TestCase):
        def test_fixture_shape(self):
            self.assertEqual(json.loads(FIXTURE)["schema"], 1)
        def test_required_invariant(self):
            self.assertFalse(fail, "故意讓合成不變條件失敗")
    return unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Example)
    ).wasSuccessful()


def self_test():
    class GateTests(unittest.TestCase):
        def test_pass(self):
            report, code = run_gate()
            self.assertEqual(code, 0)
            self.assertEqual([x["status"] for x in report["stages"]], ["pass", "pass"])
        def test_stop(self):
            report, code = run_gate(inject="tests")
            self.assertEqual(code, 1)
            self.assertEqual([x["status"] for x in report["stages"]], ["fail", "skip"])
        def test_tamper(self):
            report, code = run_gate(inject="artifact")
            self.assertEqual(code, 1)
            self.assertEqual([x["status"] for x in report["stages"]], ["pass", "fail"])
        def test_timeout(self):
            report, code = run_gate(timeout=0)
            self.assertEqual(code, 1)
            self.assertEqual(report["stages"][0]["reason"], "timeout")
    return unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(GateTests)
    ).wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", action="store_true")
    group.add_argument("--fixture-tests", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--inject", choices=["none", "tests", "artifact"], default="none")
    args = parser.parse_args()
    if args.fixture_tests:
        return 0 if fixture_tests(args.inject == "tests") else 1
    if args.test:
        return 0 if self_test() else 1
    report, code = run_gate(inject=args.inject)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if code:
        print("品質閘門拒絕；請檢查 JSON 的各階段狀態。", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
