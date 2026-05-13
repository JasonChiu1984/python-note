from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from type_contract_engineering.contracts import build_contract_report, validate_payload, write_contract_report  # noqa: E402
from type_contract_engineering.service import GatewayService, InMemoryAlarmPublisher  # noqa: E402


def main() -> int:
    payload = {
        "schema_version": "1.0",
        "device_id": "M241-AHU-01",
        "point": "AI_Temp_Supply",
        "value": 39.2,
        "unit": "C",
        "timestamp": 1778673600,
        "status": "ok",
    }
    publisher = InMemoryAlarmPublisher()
    service = GatewayService(publisher=publisher)
    reading = validate_payload(payload)
    alarm = service.evaluate(reading, now_epoch=1778673610)
    stale_reading = validate_payload({**payload, "value": 22.0, "timestamp": 1778673500, "status": "stale"})
    fail_safe = service.evaluate(stale_reading, now_epoch=1778673610)
    report = build_contract_report(
        validation_passed=True,
        alarm_checked=alarm is not None,
        fail_safe_checked=fail_safe is not None and fail_safe.fail_safe_required,
    )
    write_contract_report(ROOT / "type_contract_report.json", report)
    if alarm and fail_safe and fail_safe.fail_safe_required and report.model_has_type_hints:
        print("type contract smoke passed: schema + alarm + fail-safe + evidence")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
