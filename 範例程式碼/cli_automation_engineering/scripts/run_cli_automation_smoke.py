from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cli_automation_engineering.cli import run


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        manifest = root / "manifest.json"
        dry_run_report = root / "dry-run-report.json"
        apply_report = root / "apply-report.json"
        manifest.write_text(
            json.dumps(
                {
                    "items": [
                        {"id": "job-1", "action": "sync", "target": "gateway-a", "owner": "ops"},
                        {"id": "job-2", "action": "sync", "target": "gateway-b", "owner": "ops", "enabled": False},
                        {"id": "job-3", "action": "sync", "target": "gateway-c", "owner": "ops"},
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        dry_run_code = run(["apply", "--manifest", str(manifest), "--output", str(dry_run_report), "--dry-run"])
        if dry_run_code != 2:
            raise SystemExit(f"unexpected dry-run exit code: {dry_run_code}")

        apply_code = run(["apply", "--manifest", str(manifest), "--output", str(apply_report)])
        if apply_code != 2:
            raise SystemExit(f"unexpected apply exit code: {apply_code}")

        payload = json.loads(apply_report.read_text(encoding="utf-8"))
        if payload["executed"] != 2 or payload["blocked"] != 1:
            raise SystemExit("unexpected apply report counts")

    print("cli automation smoke passed: plan/apply/report + dry-run + exit-code + evidence")


if __name__ == "__main__":
    main()
