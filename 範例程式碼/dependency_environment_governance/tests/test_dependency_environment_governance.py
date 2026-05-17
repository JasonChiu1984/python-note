from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from dependency_environment_governance.policy import GovernanceError, evaluate_governance, render_report


FIXTURE = Path(__file__).resolve().parents[1]


class DependencyEnvironmentGovernanceTests(unittest.TestCase):
    def test_report_generation(self) -> None:
        report = evaluate_governance(FIXTURE)
        self.assertTrue(report["evidence"]["governance_passed"])
        self.assertIn("fastapi", report["dependency_policy"]["prod_dependencies"])

    def test_render_report_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            render_report(FIXTURE, output)
            self.assertTrue(output.exists())
            self.assertIn('"governance_passed": true', output.read_text(encoding="utf-8"))

    def test_dev_requirements_must_reference_prod(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "requirements.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
            (base / "requirements-dev.txt").write_text("pytest==8.3.3\n", encoding="utf-8")
            (base / "constraints.txt").write_text("fastapi==0.115.0\npytest==8.3.3\n", encoding="utf-8")
            with self.assertRaises(GovernanceError):
                evaluate_governance(base)

    def test_constraints_must_cover_all_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "requirements.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
            (base / "requirements-dev.txt").write_text("-r requirements.txt\npytest==8.3.3\n", encoding="utf-8")
            (base / "constraints.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
            with self.assertRaises(GovernanceError):
                evaluate_governance(base)

    def test_unpinned_dependency_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "requirements.txt").write_text("fastapi>=0.115.0\n", encoding="utf-8")
            (base / "requirements-dev.txt").write_text("-r requirements.txt\npytest==8.3.3\n", encoding="utf-8")
            (base / "constraints.txt").write_text("fastapi==0.115.0\npytest==8.3.3\n", encoding="utf-8")
            with self.assertRaises(GovernanceError):
                evaluate_governance(base)
