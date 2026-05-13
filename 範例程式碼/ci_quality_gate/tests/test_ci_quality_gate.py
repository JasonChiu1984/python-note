from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ci_quality_gate.checks import (
    CheckResult,
    GateReport,
    build_release_evidence,
    check_coverage_policy,
    check_runtime_matrix,
    check_workflow_contract,
)
from ci_quality_gate.pipeline import CIJob, Pipeline


class QualityGateTests(unittest.TestCase):
    def test_coverage_policy_blocks_low_coverage(self) -> None:
        result = check_coverage_policy(covered_items=7, total_items=10, floor=80)
        self.assertFalse(result.passed)
        self.assertTrue(result.blocking)

    def test_runtime_matrix_marks_beta_non_blocking(self) -> None:
        stable, beta = check_runtime_matrix("3.14", "3.15-dev")
        self.assertTrue(stable.passed)
        self.assertTrue(beta.passed)
        self.assertFalse(beta.blocking)

    def test_gate_report_allows_non_blocking_failure(self) -> None:
        report = GateReport(
            version="0.1.0",
            commit="abc123",
            results=(
                CheckResult("unit", True, "ok"),
                CheckResult("beta", False, "preview failed", blocking=False),
            ),
        )
        self.assertTrue(report.passed)

    def test_release_evidence_is_json(self) -> None:
        report = GateReport(version="0.1.0", commit="abc123", results=(CheckResult("unit", True, "ok"),))
        evidence = build_release_evidence(report)
        self.assertIn('"passed": true', evidence)
        self.assertIn('"commit": "abc123"', evidence)

    def test_workflow_contract_detects_required_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "python-ci.yml"
            path.write_text("pull_request\npush\nworkflow_dispatch\n3.14\n3.15-dev\ncompile\ntest\n", encoding="utf-8")
            self.assertTrue(check_workflow_contract(path).passed)

    def test_pipeline_stops_on_blocking_failure(self) -> None:
        jobs = [
            CIJob("compile", lambda: CheckResult("compile", False, "syntax error"), blocking=True),
            CIJob("test", lambda: CheckResult("test", True, "should not run"), blocking=True),
        ]
        results = Pipeline(jobs).run()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "compile")


if __name__ == "__main__":
    unittest.main()
