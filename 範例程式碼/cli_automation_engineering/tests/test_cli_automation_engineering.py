from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cli_automation_engineering.cli import run
from cli_automation_engineering.engine import EXIT_PARTIAL, EXIT_SUCCESS, EXIT_VALIDATION


class CliAutomationEngineeringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.manifest = self.root / "manifest.json"
        self.report = self.root / "report.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_manifest(self, items: list[dict[str, object]]) -> None:
        self.manifest.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_plan_returns_partial_when_disabled_item_exists(self) -> None:
        self.write_manifest(
            [
                {"id": "job-1", "action": "sync", "target": "gateway-a", "owner": "ops"},
                {"id": "job-2", "action": "sync", "target": "gateway-b", "owner": "ops", "enabled": False},
            ]
        )
        code = run(["plan", "--manifest", str(self.manifest), "--output", str(self.report)])
        self.assertEqual(code, EXIT_PARTIAL)
        payload = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(payload["validated"], 1)
        self.assertEqual(payload["blocked"], 1)

    def test_apply_dry_run_does_not_execute_items(self) -> None:
        self.write_manifest([{"id": "job-1", "action": "deploy", "target": "edge-1", "owner": "release"}])
        code = run(["apply", "--manifest", str(self.manifest), "--output", str(self.report), "--dry-run"])
        self.assertEqual(code, EXIT_SUCCESS)
        payload = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["executed"], 0)
        self.assertEqual(payload["items"][0]["result"], "dry-run")

    def test_invalid_manifest_returns_validation_exit_code(self) -> None:
        self.write_manifest([{"id": "job-1", "action": "deploy", "target": "edge-1"}])
        code = run(["plan", "--manifest", str(self.manifest), "--output", str(self.report)])
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertFalse(self.report.exists())

    def test_report_command_reads_existing_report(self) -> None:
        self.report.write_text(
            json.dumps(
                {
                    "mode": "apply",
                    "dry_run": False,
                    "validated": 2,
                    "blocked": 0,
                    "executed": 2,
                    "status": "success",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        code = run(["report", "--input", str(self.report)])
        self.assertEqual(code, EXIT_SUCCESS)


if __name__ == "__main__":
    unittest.main()
