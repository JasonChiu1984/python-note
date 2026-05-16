from __future__ import annotations

import tempfile
from pathlib import Path

from data_evolution_governance.migration import Checkpoint, backfill_records, preflight_check
from data_evolution_governance.report import write_migration_report
from data_evolution_governance.testing import sample_manifest, sample_records


def main() -> None:
    records = sample_records()
    issues = preflight_check(records)
    if issues:
        raise SystemExit(f"unexpected preflight issues: {issues}")
    checkpoint = Checkpoint()
    first_pass, partial = backfill_records(records, checkpoint=checkpoint, stop_after=2)
    resumed, summary = backfill_records(first_pass + records[2:], checkpoint=checkpoint)
    if partial.last_processed_id != 2:
        raise SystemExit("checkpoint did not advance to expected id")
    if summary.last_processed_id < 2 or not summary.rollback_validated:
        raise SystemExit("rollback validation failed")
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "migration_report.json"
        write_migration_report(report_path, manifest=sample_manifest(), summary=summary, preflight_issues=issues)
        if not report_path.exists():
            raise SystemExit("migration report not written")
    if not any(int(item.get("schema_version", 1)) == 2 for item in resumed):
        raise SystemExit("records were not upgraded")
    print("data evolution smoke passed: compat + checkpoint + rollback + evidence")


if __name__ == "__main__":
    main()
