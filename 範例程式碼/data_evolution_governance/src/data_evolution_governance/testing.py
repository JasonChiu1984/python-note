from __future__ import annotations

from .migration import MigrationManifest


def sample_manifest() -> MigrationManifest:
    return MigrationManifest(
        from_version=1,
        to_version=2,
        expand_steps=("add severity", "add device_group", "keep level for compat"),
        contract_condition="legacy reader verified and backfill report has zero drift",
    )


def sample_records() -> list[dict[str, object]]:
    return [
        {"record_id": 1, "device_id": "boiler-01", "timestamp": "2026-05-16T12:00:00Z", "value": 41.2, "level": "warning", "schema_version": 1},
        {"record_id": 2, "device_id": "boiler-02", "timestamp": "2026-05-16T12:00:05Z", "value": 39.4, "level": "info", "schema_version": 1},
        {"record_id": 3, "device_id": "boiler-03", "timestamp": "2026-05-16T12:00:10Z", "value": 52.6, "severity": "critical", "device_group": "heat", "schema_version": 2},
    ]


def drift_record() -> dict[str, object]:
    return {"record_id": 99, "timestamp": "2026-05-16T12:00:59Z", "value": 12.0, "schema_version": 1}
