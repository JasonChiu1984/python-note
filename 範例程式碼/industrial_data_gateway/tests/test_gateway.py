from __future__ import annotations

import json
import unittest

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
