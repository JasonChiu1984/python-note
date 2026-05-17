from __future__ import annotations

from project_delivery_blueprint.config import ServiceConfig
from project_delivery_blueprint.domain import Snapshot
from project_delivery_blueprint.service import DeliveryCoordinator, MemoryOutbox, build_release_evidence


def main() -> None:
    config = ServiceConfig.from_mapping(
        {
            "site_name": "plant-a",
            "poll_interval_seconds": "15",
            "temperature_alarm_c": "41.5",
            "max_batch_size": "4",
        }
    )
    outbox = MemoryOutbox()
    service = DeliveryCoordinator(config=config, outbox=outbox)
    report = service.run_cycle(
        [
            Snapshot(device_id="ahu-01", message_id="m-001", temperature_c=36.2, status="ok"),
            Snapshot(device_id="ahu-01", message_id="m-001", temperature_c=36.2, status="ok"),
            Snapshot(device_id="oven-02", message_id="m-002", temperature_c=46.8, status="warning"),
        ]
    )
    evidence = build_release_evidence(report)

    assert report.processed_count == 2
    assert report.duplicate_count == 1
    assert report.alarm_count == 1
    assert outbox.events[0]["kind"] == "device.snapshot.accepted"
    assert evidence["release_gate"] == "pass"
    print("project delivery smoke passed: config + dedup + alarm + release evidence")


if __name__ == "__main__":
    main()
