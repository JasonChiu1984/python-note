from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from type_contract_engineering.contracts import build_contract_report, validate_payload, write_contract_report
from type_contract_engineering.models import ReadingStatus
from type_contract_engineering.service import GatewayService, InMemoryAlarmPublisher


BASE_PAYLOAD = {
    "schema_version": "1.0",
    "device_id": "M241-AHU-01",
    "point": "AI_Temp_Supply",
    "value": 24.5,
    "unit": "C",
    "timestamp": 1778673600,
    "status": "ok",
}


class TypeContractEngineeringTests(unittest.TestCase):
    def test_validate_payload_builds_domain_model(self) -> None:
        reading = validate_payload(dict(BASE_PAYLOAD))
        self.assertEqual(reading.device_id, "M241-AHU-01")
        self.assertEqual(reading.status, ReadingStatus.OK)

    def test_validate_payload_rejects_missing_key(self) -> None:
        payload = dict(BASE_PAYLOAD)
        payload.pop("unit")
        with self.assertRaisesRegex(ValueError, "missing payload keys"):
            validate_payload(payload)

    def test_alarm_event_is_published_above_threshold(self) -> None:
        publisher = InMemoryAlarmPublisher()
        service = GatewayService(publisher=publisher, alarm_threshold_c=38.0)
        reading = validate_payload({**BASE_PAYLOAD, "value": 39.0})
        event = service.evaluate(reading, now_epoch=1778673601)
        self.assertIsNotNone(event)
        self.assertEqual(len(publisher.events), 1)
        self.assertEqual(publisher.events[0].severity, "warning")

    def test_stale_reading_requires_fail_safe(self) -> None:
        publisher = InMemoryAlarmPublisher()
        service = GatewayService(publisher=publisher, stale_timeout_seconds=30)
        reading = validate_payload({**BASE_PAYLOAD, "timestamp": 1778673500})
        event = service.evaluate(reading, now_epoch=1778673600)
        self.assertIsNotNone(event)
        self.assertTrue(event.fail_safe_required)

    def test_contract_report_contains_required_evidence(self) -> None:
        report = build_contract_report(validation_passed=True, alarm_checked=True, fail_safe_checked=True)
        self.assertTrue(report.model_has_type_hints)
        self.assertIn("device_id", report.required_keys)

    def test_contract_report_is_written_as_json(self) -> None:
        report = build_contract_report(validation_passed=True, alarm_checked=True, fail_safe_checked=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "type_contract_report.json"
            write_contract_report(path, report)
            text = path.read_text(encoding="utf-8")
        self.assertIn('"schema_version": "1.0"', text)
        self.assertIn('"fail_safe_checked": true', text)


if __name__ == "__main__":
    unittest.main()
