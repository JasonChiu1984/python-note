from __future__ import annotations

from dataclasses import dataclass

from .models import DataEvolutionError, LegacyReader, read_record


@dataclass(frozen=True)
class MigrationManifest:
    from_version: int
    to_version: int
    expand_steps: tuple[str, ...]
    contract_condition: str


@dataclass
class Checkpoint:
    last_processed_id: int = 0


@dataclass(frozen=True)
class MigrationSummary:
    upgraded: int
    skipped: int
    drifted: int
    last_processed_id: int
    rollback_validated: bool


def preflight_check(records: list[dict[str, object]]) -> list[str]:
    issues: list[str] = []
    required = {"record_id", "device_id", "timestamp", "value"}
    for payload in records:
        missing = sorted(required - payload.keys())
        if missing:
            issues.append(f"record {payload.get('record_id', 'unknown')}: missing {','.join(missing)}")
    return issues


def apply_expand(payload: dict[str, object]) -> dict[str, object]:
    record = read_record(payload)
    expanded = record.to_payload()
    expanded["schema_version"] = 2
    expanded["severity"] = record.severity
    expanded["device_group"] = record.device_group
    return expanded


def backfill_records(
    records: list[dict[str, object]],
    *,
    checkpoint: Checkpoint | None = None,
    stop_after: int | None = None,
) -> tuple[list[dict[str, object]], MigrationSummary]:
    active_checkpoint = checkpoint or Checkpoint()
    upgraded = 0
    skipped = 0
    drifted = 0
    output: list[dict[str, object]] = []
    processed_in_run = 0
    for payload in records:
        record_id = int(payload.get("record_id", 0))
        if record_id <= active_checkpoint.last_processed_id:
            output.append(payload)
            skipped += 1
            continue
        try:
            expanded = apply_expand(payload)
        except (KeyError, TypeError, ValueError, DataEvolutionError):
            drifted += 1
            output.append(payload)
            continue
        output.append(expanded)
        upgraded += 1
        active_checkpoint.last_processed_id = record_id
        processed_in_run += 1
        if stop_after is not None and processed_in_run >= stop_after:
            break
    rollback_validated = all("level" in LegacyReader().read(item) for item in output if int(item.get("schema_version", 1)) == 2)
    return output, MigrationSummary(
        upgraded=upgraded,
        skipped=skipped,
        drifted=drifted,
        last_processed_id=active_checkpoint.last_processed_id,
        rollback_validated=rollback_validated,
    )
