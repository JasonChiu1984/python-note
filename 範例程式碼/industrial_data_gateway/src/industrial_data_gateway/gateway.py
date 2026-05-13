from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from time import monotonic
from typing import Iterable, Mapping


class GatewayError(RuntimeError):
    """Raised when the gateway cannot produce a safe reading."""


@dataclass(frozen=True)
class GatewayPoint:
    point_id: str
    description: str
    modbus_register: int
    function_code: int
    register_type: str
    data_type: str
    word_order: str
    scale: float
    unit: str
    low_alarm: float | None
    high_alarm: float | None
    fail_safe_value: float | int | bool
    opcua_node_id: str
    bacnet_object_type: str
    bacnet_object_instance: int
    mqtt_topic: str


@dataclass(frozen=True)
class PointReading:
    point_id: str
    value: float | int | bool
    unit: str
    quality: str
    age_seconds: float


@dataclass(frozen=True)
class AlarmEvent:
    point_id: str
    severity: str
    message: str
    value: float | int | bool


def decode_float32_words(high_word: int, low_word: int, word_order: str = "big") -> float:
    if not 0 <= high_word <= 0xFFFF or not 0 <= low_word <= 0xFFFF:
        raise GatewayError("Modbus words must be 16-bit unsigned values")
    words = (high_word, low_word) if word_order == "big" else (low_word, high_word)
    raw = struct.pack(">HH", *words)
    return struct.unpack(">f", raw)[0]


def encode_float32_words(value: float, word_order: str = "big") -> tuple[int, int]:
    raw = struct.pack(">f", float(value))
    high_word, low_word = struct.unpack(">HH", raw)
    return (high_word, low_word) if word_order == "big" else (low_word, high_word)


class MockModbusDevice:
    def __init__(self, registers: Mapping[int, int], response_delay_seconds: float = 0.0) -> None:
        self._registers = dict(registers)
        self.response_delay_seconds = response_delay_seconds

    def read_holding_registers(self, start_register: int, count: int, timeout_seconds: float) -> list[int]:
        if self.response_delay_seconds > timeout_seconds:
            raise TimeoutError(f"Modbus read timeout after {timeout_seconds:.1f}s")
        values: list[int] = []
        for offset in range(count):
            register = start_register + offset
            if register not in self._registers:
                raise GatewayError(f"Missing holding register 4{register:04d}")
            values.append(self._registers[register])
        return values


class IndustrialGateway:
    def __init__(self, points: Iterable[GatewayPoint], device: MockModbusDevice, timeout_seconds: float = 2.0, stale_seconds: float = 15.0) -> None:
        self.points = list(points)
        self.device = device
        self.timeout_seconds = timeout_seconds
        self.stale_seconds = stale_seconds

    def poll_once(self) -> tuple[list[PointReading], list[AlarmEvent]]:
        readings: list[PointReading] = []
        alarms: list[AlarmEvent] = []
        started = monotonic()
        for point in self.points:
            try:
                reading = self._read_point(point, started)
            except (GatewayError, TimeoutError) as exc:
                reading = PointReading(
                    point_id=point.point_id,
                    value=point.fail_safe_value,
                    unit=point.unit,
                    quality="FAIL_SAFE",
                    age_seconds=self.stale_seconds,
                )
                alarms.append(AlarmEvent(point.point_id, "critical", str(exc), point.fail_safe_value))
            else:
                alarms.extend(self._evaluate_alarm(point, reading))
            readings.append(reading)
        return readings, alarms

    def _read_point(self, point: GatewayPoint, started: float) -> PointReading:
        if point.function_code != 3 or point.register_type != "holding":
            raise GatewayError("sample supports FC03 holding register reads")
        count = 2 if point.data_type == "float32" else 1
        words = self.device.read_holding_registers(point.modbus_register, count, self.timeout_seconds)
        value: float | int | bool
        if point.data_type == "float32":
            value = decode_float32_words(words[0], words[1], point.word_order) * point.scale
            if math.isnan(value) or math.isinf(value):
                raise GatewayError("invalid float reading")
        elif point.data_type == "bool":
            value = bool(words[0])
        else:
            value = int(words[0] * point.scale)
        age = monotonic() - started
        quality = "STALE" if age > self.stale_seconds else "GOOD"
        return PointReading(point.point_id, value, point.unit, quality, age)

    def _evaluate_alarm(self, point: GatewayPoint, reading: PointReading) -> list[AlarmEvent]:
        if reading.quality != "GOOD":
            return [AlarmEvent(point.point_id, "warning", f"{point.point_id} quality is {reading.quality}", reading.value)]
        if isinstance(reading.value, bool):
            return []
        alarms: list[AlarmEvent] = []
        if point.low_alarm is not None and reading.value < point.low_alarm:
            alarms.append(AlarmEvent(point.point_id, "warning", f"{point.point_id} below low alarm", reading.value))
        if point.high_alarm is not None and reading.value > point.high_alarm:
            alarms.append(AlarmEvent(point.point_id, "critical", f"{point.point_id} above high alarm", reading.value))
        return alarms

    def build_gateway_report(self, readings: list[PointReading], alarms: list[AlarmEvent]) -> dict[str, object]:
        point_by_id = {point.point_id: point for point in self.points}
        return {
            "site": "TW-Plant-01",
            "polling": {"interval_seconds": 5.0, "timeout_seconds": self.timeout_seconds, "retry": 2},
            "opcua": {
                "endpoint_url": "opc.tcp://192.168.10.20:4840",
                "security_mode": "None",
                "subscription_publish_seconds": 1.0,
                "keepalive_seconds": 10.0,
                "reconnect_backoff_seconds": [1, 5, 15],
                "nodes": [
                    {"node_id": point_by_id[item.point_id].opcua_node_id, "value": item.value, "quality": item.quality}
                    for item in readings
                ],
            },
            "bacnet": {
                "network": "BACnet/IP",
                "bbmd": "192.168.10.2",
                "foreign_device_ttl_seconds": 60,
                "routing": "site VLAN 20 to SCADA VLAN 30 through industrial firewall",
                "objects": [
                    {
                        "object_type": point_by_id[item.point_id].bacnet_object_type,
                        "object_instance": point_by_id[item.point_id].bacnet_object_instance,
                        "present_value": item.value,
                    }
                    for item in readings
                ],
            },
            "mqtt": [
                {
                    "topic": point_by_id[item.point_id].mqtt_topic,
                    "qos": 1,
                    "payload": json.dumps({"value": item.value, "unit": item.unit, "quality": item.quality}, sort_keys=True),
                }
                for item in readings
            ],
            "alarms": [alarm.__dict__ for alarm in alarms],
            "fail_safe_active": any(item.quality == "FAIL_SAFE" for item in readings),
        }


def default_points() -> list[GatewayPoint]:
    return [
        GatewayPoint(
            point_id="boiler_supply_temp",
            description="Boiler supply water temperature",
            modbus_register=1,
            function_code=3,
            register_type="holding",
            data_type="float32",
            word_order="big",
            scale=1.0,
            unit="degC",
            low_alarm=5.0,
            high_alarm=80.0,
            fail_safe_value=0.0,
            opcua_node_id="ns=2;s=Boiler.SupplyTemperature",
            bacnet_object_type="analog-input",
            bacnet_object_instance=1,
            mqtt_topic="plant/tw01/boiler/supply_temperature",
        ),
        GatewayPoint(
            point_id="pump_run_feedback",
            description="Primary pump run feedback",
            modbus_register=11,
            function_code=3,
            register_type="holding",
            data_type="bool",
            word_order="n/a",
            scale=1.0,
            unit="state",
            low_alarm=None,
            high_alarm=None,
            fail_safe_value=False,
            opcua_node_id="ns=2;s=Pump.RunFeedback",
            bacnet_object_type="binary-input",
            bacnet_object_instance=2,
            mqtt_topic="plant/tw01/pump/run_feedback",
        ),
    ]
