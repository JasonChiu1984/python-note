from __future__ import annotations

import json

from .gateway import IndustrialGateway, MockModbusDevice, default_points, encode_float32_words


def main() -> int:
    high, low = encode_float32_words(42.5, word_order="big")
    device = MockModbusDevice({1: high, 2: low, 11: 1})
    gateway = IndustrialGateway(default_points(), device)
    readings, alarms = gateway.poll_once()
    print(json.dumps(gateway.build_gateway_report(readings, alarms), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
