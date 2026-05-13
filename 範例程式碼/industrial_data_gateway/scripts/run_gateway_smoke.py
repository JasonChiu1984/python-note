from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from industrial_data_gateway.gateway import IndustrialGateway, MockModbusDevice, default_points, encode_float32_words


def main() -> int:
    high, low = encode_float32_words(42.5, word_order="big")
    device = MockModbusDevice({1: high, 2: low, 11: 1})
    gateway = IndustrialGateway(default_points(), device, timeout_seconds=2.0)
    readings, alarms = gateway.poll_once()
    report = gateway.build_gateway_report(readings, alarms)

    assert len(readings) == 2
    assert report["opcua"]["endpoint_url"] == "opc.tcp://192.168.10.20:4840"
    assert report["opcua"]["security_mode"] == "None"
    assert report["bacnet"]["bbmd"] == "192.168.10.2"
    assert report["mqtt"][0]["qos"] == 1
    assert not report["fail_safe_active"]

    print("industrial gateway smoke passed: modbus + opcua + bacnet + mqtt + alarms")
    print(json.dumps({"readings": len(readings), "alarms": len(alarms)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
