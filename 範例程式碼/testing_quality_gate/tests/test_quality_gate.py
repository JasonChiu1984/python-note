from __future__ import annotations

import importlib.util
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
