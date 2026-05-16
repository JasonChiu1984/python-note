from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from data_evolution_governance.migration import Checkpoint, backfill_records, preflight_check
from data_evolution_governance.models import LegacyReader, read_record
from data_evolution_governance.report import write_migration_report
from data_evolution_governance.testing import drift_record, sample_manifest, sample_records


class DataEvolutionGovernanceTests(unittest.TestCase):
    def test_read_record_supports_v1_payload(self) -> None:
        record = read_record(sample_records()[0])
        self.assertEqual(record.severity, "warning")
        self.assertEqual(record.schema_version, 2)

    def test_backfill_updates_checkpoint(self) -> None:
        checkpoint = Checkpoint()
        upgraded, summary = backfill_records(sample_records(), checkpoint=checkpoint, stop_after=2)
        self.assertEqual(summary.last_processed_id, 2)
        self.assertTrue(any(int(item.get("schema_version", 1)) == 2 for item in upgraded))

    def test_resume_skips_processed_records(self) -> None:
        checkpoint = Checkpoint(last_processed_id=2)
        _, summary = backfill_records(sample_records(), checkpoint=checkpoint)
        self.assertEqual(summary.skipped, 2)

    def test_preflight_detects_drift(self) -> None:
        issues = preflight_check(sample_records() + [drift_record()])
        self.assertEqual(len(issues), 1)
        self.assertIn("missing device_id", issues[0])

    def test_legacy_reader_can_read_upgraded_record(self) -> None:
        upgraded, _ = backfill_records(sample_records())
        legacy = LegacyReader().read(upgraded[0])
        self.assertEqual(legacy["level"], "warning")
        self.assertEqual(legacy["schema_version"], 1)

    def test_report_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _, summary = backfill_records(sample_records())
            target = Path(tmpdir) / "migration_report.json"
            write_migration_report(target, manifest=sample_manifest(), summary=summary, preflight_issues=[])
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["manifest"]["to_version"], 2)
        self.assertTrue(payload["summary"]["rollback_validated"])


if __name__ == "__main__":
    unittest.main()
