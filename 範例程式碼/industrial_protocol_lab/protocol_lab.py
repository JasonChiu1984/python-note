"""Eight read-only protocol mapping exercises. Run with Python 3.11+."""

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import struct
from typing import Literal

Quality = Literal["good", "uncertain", "bad"]


@dataclass(frozen=True)
class Reading:
    source: str
    value_c: float | None
    quality: Quality


def temperature(source: str, value: float, quality: Quality = "good") -> Reading:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite temperature")
    return Reading(source, float(value) if quality != "bad" else None, quality)


def modbus_float(registers: list[int], *, low_word_first: bool = False) -> float:
    if len(registers) != 2 or any(type(x) is not int or not 0 <= x <= 65535 for x in registers):
        raise ValueError("Expected two unsigned 16-bit registers")
    high, low = registers[::-1] if low_word_first else registers
    return struct.unpack(">f", struct.pack(">HH", high, low))[0]


def modbus_demo() -> Reading:
    # Unit 7, FC03, zero-based start address 0, count 2. Sample response words.
    return temperature("modbus:7/holding/0", modbus_float([0x41B0, 0x0000]))


def bacnet_demo() -> Reading:
    # Typed ReadProperty results after BACnet decoding. Units 62 = degrees Celsius.
    props = {"presentValue": 22.0, "units": 62, "statusFlags": [False, False, False, False]}
    in_alarm, fault, overridden, out_of_service = props["statusFlags"]
    if props["units"] != 62:
        raise ValueError("BACnet point must use degrees Celsius")
    quality = "bad" if fault or out_of_service else "uncertain" if overridden else "good"
    # in_alarm is the process alarm state. It does not invalidate the reading.
    return temperature("bacnet:device/420101/analogInput/1", props["presentValue"], quality)


def opcua_demo() -> Reading:
    # DataValue decoded by the OPC UA SDK. The upper two bits are severity.
    data = {"value": 22.0, "status": 0x40000000, "source_timestamp": "2026-11-24T08:00:00Z"}
    severity = data["status"] >> 30
    status = ("good", "uncertain", "bad", "bad")[severity]
    return temperature("opcua:urn:example:plant/AHU01.SAT", data["value"], status)


def mqtt_read(topic: str, payload: bytes) -> Reading:
    message = json.loads(payload)
    if message["schema"] != 1 or message["point"] != "AHU01.SAT":
        raise ValueError("Unsupported telemetry contract")
    quality = message["quality"]
    if quality not in {"good", "uncertain", "bad"} or message["unit"] != "degC":
        raise ValueError("Unexpected quality or unit")
    if quality == "bad" and message["value"] is None:
        return Reading(f"mqtt:{topic}", None, "bad")
    return temperature(f"mqtt:{topic}", message["value"], quality)


def mqtt_demo() -> Reading:
    payload = b'{"schema":1,"point":"AHU01.SAT","value":22.0,"unit":"degC","quality":"good"}'
    return mqtt_read("site/lab/ahu01/telemetry", payload)


def zigbee_read(topic: str, payload: bytes) -> Reading:
    # Zigbee2MQTT has already converted ZCL hundredths to a temperature in °C.
    message = json.loads(payload)
    if "temperature" not in message:
        raise ValueError("State message does not contain a temperature update")
    return temperature(f"zigbee:{topic}", message["temperature"])


def zigbee_demo() -> Reading:
    return zigbee_read("zigbee2mqtt/ahu01-room", b'{"temperature":22.0,"battery":95,"linkquality":128}')


def read_input_image(protocol: str, point: str, payload: bytes, quality: Quality) -> Reading:
    # The PLC's export contract fixes a 16-bit signed big-endian field and 0.1 °C scaling.
    # Read only a consistent PLC snapshot and reject failed stations before decoding.
    source = f"{protocol}:{point}"
    if quality == "bad":
        return Reading(source, None, quality)
    if len(payload) != 2:
        raise ValueError("Expected exactly two input bytes")
    (deci_c,) = struct.unpack(">h", payload)
    return temperature(source, deci_c / 10, quality)


def fieldbus_read(protocol: str, snapshot: dict) -> Reading:
    if protocol == "profinet":
        point = f"{snapshot['device']}/{snapshot['slot']}/{snapshot['subslot']}"
        valid = snapshot["valid"]
    elif protocol == "profibus":
        point = f"station/{snapshot['station']}/I{snapshot['input_offset']}"
        valid = snapshot["data_exchange"]
    else:
        point = f"station/{snapshot['station']}/RWr0"
        valid = snapshot["link_ok"]

    if type(valid) is not bool:
        raise ValueError("Expected a Boolean station or submodule status")
    if not valid:
        return Reading(f"{protocol}:{point}", None, "bad")
    if protocol == "cc-link":
        word = snapshot["rwr0"]
        if type(word) is not int or not 0 <= word < 65536:
            raise ValueError("Expected an unsigned RWr word")
        payload = word.to_bytes(2, "big")
    else:
        payload = bytes.fromhex(snapshot["bytes"])
    return read_input_image(protocol, point, payload, "good")


FIELDBUS_FIXTURES = {
    "profinet": {"device": "ahu01-io", "slot": 2, "subslot": 1, "valid": True, "bytes": "00 DC"},
    "profibus": {"station": 5, "input_offset": 0, "data_exchange": True, "bytes": "00 DC"},
    "cc-link": {"station": 1, "rwr0": 0x00DC, "link_ok": True},
}


DEMOS = {
    "modbus": modbus_demo,
    "bacnet": bacnet_demo,
    "opcua": opcua_demo,
    "mqtt": mqtt_demo,
    "zigbee": zigbee_demo,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    protocols = [*DEMOS, *FIELDBUS_FIXTURES]
    parser.add_argument("protocol", choices=[*protocols, "all"], nargs="?", default="all")
    parser.add_argument("--snapshot", type=Path, help="JSON from the PLC or master gateway")
    args = parser.parse_args()
    if args.snapshot is not None and args.protocol not in FIELDBUS_FIXTURES:
        parser.error("--snapshot is for a single PROFINET, PROFIBUS or CC-Link example")

    for name in protocols if args.protocol == "all" else [args.protocol]:
        if name in FIELDBUS_FIXTURES:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else FIELDBUS_FIXTURES[name]
            reading = fieldbus_read(name, snapshot)
        else:
            reading = DEMOS[name]()
        print(json.dumps({"protocol": name, **asdict(reading)}, allow_nan=False))


if __name__ == "__main__":
    main()
