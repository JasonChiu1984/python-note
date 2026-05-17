from __future__ import annotations

import unittest

from project_delivery_blueprint.config import ServiceConfig
from project_delivery_blueprint.domain import Snapshot
from project_delivery_blueprint.service import DeliveryCoordinator, MemoryOutbox, build_release_evidence


class ProjectDeliveryBlueprintTest(unittest.TestCase):
    def test_config_requires_site_name(self) -> None:
        with self.assertRaises(ValueError):
            ServiceConfig.from_mapping({})

    def test_duplicate_snapshot_is_skipped(self) -> None:
        config = ServiceConfig.from_mapping({"site_name": "plant-a"})
        outbox = MemoryOutbox()
        service = DeliveryCoordinator(config=config, outbox=outbox)
        snapshots = [
            Snapshot(device_id="ahu-01", message_id="m-1", temperature_c=36.2, status="ok"),
            Snapshot(device_id="ahu-01", message_id="m-1", temperature_c=36.2, status="ok"),
        ]
        report = service.run_cycle(snapshots)
        self.assertEqual(report.processed_count, 1)
        self.assertEqual(report.duplicate_count, 1)
        self.assertEqual(len(outbox.events), 1)

    def test_alarm_snapshot_emits_fail_safe_evidence(self) -> None:
        config = ServiceConfig.from_mapping(
            {"site_name": "plant-a", "temperature_alarm_c": "40.0"}
        )
        outbox = MemoryOutbox()
        service = DeliveryCoordinator(config=config, outbox=outbox)
        report = service.run_cycle(
            [Snapshot(device_id="boiler-01", message_id="m-2", temperature_c=48.5, status="warning")]
        )
        evidence = build_release_evidence(report)
        self.assertEqual(report.alarm_count, 1)
        self.assertIn("boiler-01", report.fail_safe_devices)
        self.assertEqual(evidence["operator_action"], "notify_and_hold_high_temperature_devices")


if __name__ == "__main__":
    unittest.main()
