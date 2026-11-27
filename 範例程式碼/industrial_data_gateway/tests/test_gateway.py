from __future__ import annotations

from dataclasses import replace
import json
import unittest
from unittest.mock import Mock, patch

from industrial_data_gateway.gateway import (
    GatewayError,
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

    def test_duplicate_ids_fail_before_reading_in_both_orders(self) -> None:
        boiler, pump = default_points()
        duplicate = replace(pump, point_id=boiler.point_id)
        for points in ((boiler, duplicate), (duplicate, boiler)):
            with self.subTest(points=points):
                device = Mock(spec=MockModbusDevice)
                with self.assertRaisesRegex(GatewayError, "Duplicate point_id: boiler_supply_temp"):
                    IndustrialGateway(iter(points), device)
                device.read_holding_registers.assert_not_called()

    def test_one_shot_mapping_preserves_values_and_destinations(self) -> None:
        high, low = encode_float32_words(42.5)
        points = default_points()
        gateway = IndustrialGateway(iter(points), MockModbusDevice({1: high, 2: low, 11: 1}))
        readings, alarms = gateway.poll_once()
        report = gateway.build_gateway_report(readings, alarms)
        self.assertEqual(alarms, [])
        self.assertEqual([r.quality for r in readings], ["GOOD", "GOOD"])
        self.assertEqual(readings[0].value, 42.5)
        self.assertIs(readings[1].value, True)
        for i, point in enumerate(points):
            ua = report["opcua"]["nodes"][i]
            obj = report["bacnet"]["objects"][i]
            mqtt = report["mqtt"][i]
            self.assertEqual((ua["node_id"], ua["value"], ua["quality"]),
                             (point.opcua_node_id, readings[i].value, "GOOD"))
            self.assertEqual((obj["object_type"], obj["object_instance"], obj["present_value"], obj["quality"]),
                             (point.bacnet_object_type, point.bacnet_object_instance, readings[i].value, "GOOD"))
            self.assertEqual(mqtt["topic"], point.mqtt_topic)
            self.assertEqual(json.loads(mqtt["payload"]),
                             {"value": readings[i].value, "unit": point.unit, "quality": "GOOD"})

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
