from __future__ import annotations

from dataclasses import asdict, dataclass


class DataEvolutionError(ValueError):
    pass


@dataclass(frozen=True)
class TelemetryRecord:
    record_id: int
    device_id: str
    timestamp: str
    value: float
    severity: str
    device_group: str
    schema_version: int = 2
    level: str | None = None

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


def read_record(payload: dict[str, object]) -> TelemetryRecord:
    version = int(payload.get("schema_version", 1))
    if version == 1:
        severity = str(payload.get("level", "info"))
        device_group = str(payload.get("device_group", "ungrouped"))
    elif version == 2:
        severity = str(payload["severity"])
        device_group = str(payload.get("device_group", "ungrouped"))
    else:
        raise DataEvolutionError(f"unsupported schema version: {version}")
    return TelemetryRecord(
        record_id=int(payload["record_id"]),
        device_id=str(payload["device_id"]),
        timestamp=str(payload["timestamp"]),
        value=float(payload["value"]),
        severity=severity,
        device_group=device_group,
        schema_version=2,
        level=str(payload["level"]) if "level" in payload else None,
    )


class LegacyReader:
    def read(self, payload: dict[str, object]) -> dict[str, object]:
        severity = str(payload.get("severity") or payload.get("level", "info"))
        return {
            "record_id": int(payload["record_id"]),
            "device_id": str(payload["device_id"]),
            "timestamp": str(payload["timestamp"]),
            "value": float(payload["value"]),
            "level": severity,
            "schema_version": 1,
        }
