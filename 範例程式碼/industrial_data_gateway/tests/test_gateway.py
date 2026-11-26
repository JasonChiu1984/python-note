from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from industrial_data_gateway.gateway import (
    IndustrialGateway,
    MockModbusDevice,
    decode_float32_words,
    default_points,
    encode_float32_words,
)


class IndustrialGatewayTests(unittest.TestCase):
    def test_float32_big_word_order_conversion(self) -> None:
        high, low = encode_float32_words(42.5, word_order="big")
        self.assertAlmostEqual(decode_float32_words(high, low, word_order="big"), 42.5)

    def test_poll_once_builds_good_readings(self) -> None:
        high, low = encode_float32_words(42.5)
        gateway = IndustrialGateway(default_points(), MockModbusDevice({1: high, 2: low, 11: 1}))
        readings, alarms = gateway.poll_once()
        self.assertEqual([item.quality for item in readings], ["GOOD", "GOOD"])
        self.assertEqual(alarms, [])

    def test_high_alarm_is_reported(self) -> None:
        high, low = encode_float32_words(91.2)
        gateway = IndustrialGateway(default_points(), MockModbusDevice({1: high, 2: low, 11: 1}))
        _readings, alarms = gateway.poll_once()
        self.assertEqual(len(alarms), 1)
        self.assertEqual(alarms[0].severity, "critical")

    def test_timeout_uses_fail_safe_value(self) -> None:
        high, low = encode_float32_words(42.5)
        gateway = IndustrialGateway(default_points(), MockModbusDevice({1: high, 2: low, 11: 1}, response_delay_seconds=10.0), timeout_seconds=1.0)
        readings, alarms = gateway.poll_once()
        self.assertTrue(all(item.quality == "FAIL_SAFE" for item in readings))
        self.assertTrue(all(alarm.severity == "critical" for alarm in alarms))

    def test_long_scan_does_not_make_a_new_read_stale(self) -> None:
        high, low = encode_float32_words(91.2)
        gateway = IndustrialGateway(default_points()[::-1], MockModbusDevice({1: high, 2: low, 11: 1}))
        with patch("industrial_data_gateway.gateway.monotonic", side_effect=[0, 15.1]):
            readings, alarms = gateway.poll_once()
        self.assertEqual([r.quality for r in readings], ["GOOD", "GOOD"])
        self.assertEqual([r.age_seconds for r in readings], [None, None])
        self.assertEqual([(a.point_id, a.severity) for a in alarms], [("boiler_supply_temp", "critical")])
        self.assertEqual(gateway.build_gateway_report(readings, alarms)["polling"]["last_scan_duration_seconds"], 15.1)

    def test_bacnet_preview_distinguishes_stopped_from_unavailable(self) -> None:
        high, low = encode_float32_words(42.5)
        rows = []
        for delay in (0, 2):
            gateway = IndustrialGateway(default_points(), MockModbusDevice({1: high, 2: low, 11: 0}, delay),
                                        timeout_seconds=1)
            readings, alarms = gateway.poll_once()
            rows.append(gateway.build_gateway_report(readings, alarms)["bacnet"]["objects"][1])
        self.assertEqual([row["present_value"] for row in rows], [False, False])
        self.assertEqual([row["quality"] for row in rows], ["GOOD", "FAIL_SAFE"])

    def test_gateway_report_contains_protocol_contracts(self) -> None:
        high, low = encode_float32_words(42.5)
        gateway = IndustrialGateway(default_points(), MockModbusDevice({1: high, 2: low, 11: 1}))
        readings, alarms = gateway.poll_once()
        report = gateway.build_gateway_report(readings, alarms)
        self.assertEqual(report["opcua"]["security_mode"], "None")
        self.assertEqual(report["opcua"]["nodes"][0]["node_id"], "ns=2;s=Boiler.SupplyTemperature")
        self.assertEqual(report["bacnet"]["objects"][0]["object_type"], "analog-input")
        mqtt_payload = json.loads(report["mqtt"][0]["payload"])
        self.assertEqual(mqtt_payload["unit"], "degC")


if __name__ == "__main__":
    unittest.main()
