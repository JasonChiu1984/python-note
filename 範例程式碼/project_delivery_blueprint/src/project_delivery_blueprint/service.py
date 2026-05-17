from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from .config import ServiceConfig
from .domain import CycleReport, Snapshot


class MemoryOutbox:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.events.append(payload)


class DeliveryCoordinator:
    def __init__(self, config: ServiceConfig, outbox: MemoryOutbox) -> None:
        self.config = config
        self.outbox = outbox
        self._processed_ids: set[str] = set()

    def run_cycle(self, snapshots: Iterable[Snapshot]) -> CycleReport:
        processed_count = 0
        duplicate_count = 0
        alarm_count = 0
        fail_safe_devices: list[str] = []

        for snapshot in list(snapshots)[: self.config.max_batch_size]:
            if snapshot.message_id in self._processed_ids:
                duplicate_count += 1
                continue
            self._processed_ids.add(snapshot.message_id)
            processed_count += 1

            in_alarm = snapshot.temperature_c >= self.config.temperature_alarm_c
            if in_alarm:
                alarm_count += 1
                fail_safe_devices.append(snapshot.device_id)

            self.outbox.publish(
                {
                    "kind": "device.snapshot.accepted",
                    "site_name": self.config.site_name,
                    "device_id": snapshot.device_id,
                    "message_id": snapshot.message_id,
                    "temperature_c": snapshot.temperature_c,
                    "status": snapshot.status,
                    "alarm": in_alarm,
                }
            )

        return CycleReport(
            site_name=self.config.site_name,
            processed_count=processed_count,
            duplicate_count=duplicate_count,
            alarm_count=alarm_count,
            fail_safe_devices=tuple(fail_safe_devices),
        )


def build_release_evidence(report: CycleReport) -> dict[str, object]:
    evidence = asdict(report)
    evidence["release_gate"] = "pass" if report.processed_count >= 1 else "hold"
    evidence["operator_action"] = (
        "notify_and_hold_high_temperature_devices"
        if report.fail_safe_devices
        else "continue_monitoring"
    )
    return evidence
