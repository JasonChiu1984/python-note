from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


EXIT_SUCCESS = 0
EXIT_PARTIAL = 2
EXIT_VALIDATION = 3
REQUIRED_FIELDS = ("id", "action", "target", "owner")


@dataclass
class ManifestItem:
    id: str
    action: str
    target: str
    owner: str
    enabled: bool = True


@dataclass
class ExecutionReport:
    mode: str
    dry_run: bool
    validated: int
    blocked: int
    executed: int
    status: str
    items: list[dict[str, object]]


def load_manifest(path: Path) -> list[ManifestItem]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest items must be a list")
    manifest: list[ManifestItem] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("manifest item must be an object")
        missing = [field for field in REQUIRED_FIELDS if not raw.get(field)]
        if missing:
            raise ValueError(f"manifest item missing fields: {', '.join(missing)}")
        manifest.append(
            ManifestItem(
                id=str(raw["id"]),
                action=str(raw["action"]),
                target=str(raw["target"]),
                owner=str(raw["owner"]),
                enabled=bool(raw.get("enabled", True)),
            )
        )
    return manifest


def plan_manifest(items: list[ManifestItem]) -> ExecutionReport:
    report_items = []
    validated = 0
    blocked = 0
    for item in items:
        entry = asdict(item)
        if item.enabled:
            entry["decision"] = "ready"
            validated += 1
        else:
            entry["decision"] = "blocked"
            blocked += 1
        report_items.append(entry)
    status = "success" if blocked == 0 else "partial"
    return ExecutionReport("plan", True, validated, blocked, 0, status, report_items)


def apply_manifest(items: list[ManifestItem], dry_run: bool) -> ExecutionReport:
    report_items = []
    validated = 0
    blocked = 0
    executed = 0
    for item in items:
        entry = asdict(item)
        if not item.enabled:
            entry["result"] = "blocked"
            blocked += 1
        elif dry_run:
            entry["result"] = "dry-run"
            validated += 1
        else:
            entry["result"] = "executed"
            validated += 1
            executed += 1
        report_items.append(entry)
    status = "success" if blocked == 0 else "partial"
    return ExecutionReport("apply", dry_run, validated, blocked, executed, status, report_items)


def write_report(report: ExecutionReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_summary_line(report: ExecutionReport) -> str:
    return (
        f"mode={report.mode} dry_run={str(report.dry_run).lower()} "
        f"validated={report.validated} blocked={report.blocked} executed={report.executed} status={report.status}"
    )
