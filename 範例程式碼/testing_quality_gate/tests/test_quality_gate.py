from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


def load_gate_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_quality_gate.py"
    spec = importlib.util.spec_from_file_location("run_quality_gate", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load quality gate script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualityGateTest(unittest.TestCase):
    def test_quality_gate_finds_python_files(self) -> None:
        gate = load_gate_module()
        files = [path.name for path in gate.iter_python_files()]
        self.assertIn("service.py", files)
        self.assertIn("test_order_service.py", files)

    def test_quality_gate_compile_step_passes(self) -> None:
        gate = load_gate_module()
        gate.compile_all()

    def test_gate_rejects_missing_test_evidence(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_quality_gate.py"
        cases = {
            "empty": ("", "no tests executed"),
            "skip": (
                "    @unittest.skip('fixture')\n    def test_case(self): pass\n",
                "required tests were skipped or expected to fail",
            ),
            "expected_failure": (
                "    @unittest.expectedFailure\n    def test_case(self): self.fail('fixture')\n",
                "required tests were skipped or expected to fail",
            ),
            "failure": (
                "    def test_case(self): self.fail('fixture')\n",
                "unittest failed",
            ),
        }
        for name, (method, expected) in cases.items():
            with self.subTest(case=name), TemporaryDirectory() as folder:
                root = Path(folder)
                gate = root / "scripts" / script.name
                gate.parent.mkdir()
                gate.write_bytes(script.read_bytes())
                tests = root / "tests"
                tests.mkdir()
                if method:
                    (tests / "test_fixture.py").write_text(
                        "import unittest\nclass Fixture(unittest.TestCase):\n" + method,
                        encoding="utf-8",
                    )
                proc = subprocess.run(
                    [sys.executable, "-I", str(gate)], cwd=root, text=True,
                    capture_output=True, timeout=15,
                )
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(expected, proc.stderr)
                self.assertNotIn("quality gate passed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
