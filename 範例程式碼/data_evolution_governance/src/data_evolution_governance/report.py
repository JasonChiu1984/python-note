from __future__ import annotations

import json
from pathlib import Path

from .migration import MigrationManifest, MigrationSummary


def write_migration_report(
    path: Path,
    *,
    manifest: MigrationManifest,
    summary: MigrationSummary,
    preflight_issues: list[str],
) -> None:
    payload = {
        "manifest": {
            "from_version": manifest.from_version,
            "to_version": manifest.to_version,
            "expand_steps": list(manifest.expand_steps),
            "contract_condition": manifest.contract_condition,
        },
        "summary": {
            "upgraded": summary.upgraded,
            "skipped": summary.skipped,
            "drifted": summary.drifted,
            "last_processed_id": summary.last_processed_id,
            "rollback_validated": summary.rollback_validated,
        },
        "preflight_issues": preflight_issues,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
