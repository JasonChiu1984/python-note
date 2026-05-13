from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, get_type_hints

from .models import ReadingPayload, ReadingStatus, SensorReading


REQUIRED_PAYLOAD_KEYS = {
    "schema_version",
    "device_id",
    "point",
    "value",
    "unit",
    "timestamp",
    "status",
}


@dataclass(frozen=True)
class ContractReport:
    schema_version: str
    required_keys: tuple[str, ...]
    model_has_type_hints: bool
    validation_passed: bool
    alarm_checked: bool
    fail_safe_checked: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "required_keys": list(self.required_keys),
            "model_has_type_hints": self.model_has_type_hints,
            "validation_passed": self.validation_passed,
            "alarm_checked": self.alarm_checked,
            "fail_safe_checked": self.fail_safe_checked,
        }


def validate_payload(payload: dict[str, Any]) -> SensorReading:
    missing = sorted(REQUIRED_PAYLOAD_KEYS.difference(payload))
    if missing:
        raise ValueError(f"missing payload keys: {', '.join(missing)}")
    if not isinstance(payload["value"], (int, float)):
        raise ValueError("value must be numeric")
    if not isinstance(payload["timestamp"], int):
        raise ValueError("timestamp must be an integer epoch second")
    try:
        status = ReadingStatus(str(payload["status"]))
    except ValueError as exc:
        raise ValueError("status must be ok, stale, or fault") from exc
    typed_payload: ReadingPayload = {
        "schema_version": str(payload["schema_version"]),
        "device_id": str(payload["device_id"]),
        "point": str(payload["point"]),
        "value": float(payload["value"]),
        "unit": str(payload["unit"]),
        "timestamp": int(payload["timestamp"]),
        "status": status.value,
    }
    return SensorReading(
        schema_version=typed_payload["schema_version"],
        device_id=typed_payload["device_id"],
        point=typed_payload["point"],
        value=typed_payload["value"],
        unit=typed_payload["unit"],
        timestamp=typed_payload["timestamp"],
        status=status,
    )


def build_contract_report(validation_passed: bool, alarm_checked: bool, fail_safe_checked: bool) -> ContractReport:
    hints = get_type_hints(SensorReading)
    expected_hints = {"schema_version", "device_id", "point", "value", "unit", "timestamp", "status"}
    return ContractReport(
        schema_version="1.0",
        required_keys=tuple(sorted(REQUIRED_PAYLOAD_KEYS)),
        model_has_type_hints=expected_hints.issubset(hints),
        validation_passed=validation_passed,
        alarm_checked=alarm_checked,
        fail_safe_checked=fail_safe_checked,
    )


def write_contract_report(path: Path, report: ContractReport) -> None:
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
