from pathlib import Path
import runpy

import pytest


SOURCE = (Path(__file__).resolve().parents[1] /
          "extensions/python_industrial_network_congestion_tutorial/example.py")
SAMPLE = runpy.run_path(str(SOURCE))


def test_modbus_serial_guide_19200_boundary():
    assert SAMPLE["silent_ms"](19200) == pytest.approx(3.5 * 11 * 1000 / 19200)
    assert SAMPLE["silent_ms"](38400) == 1.75


@pytest.mark.parametrize(("timeout", "sweep"), [(1000, 2.4364583333), (100, 1.5364583333)])
def test_silent_station_occupies_service_but_does_not_transmit_response(timeout, sweep):
    healthy, healthy_wire = SAMPLE["transaction_ms"](19200, 20, 15)
    offline, request_wire = SAMPLE["no_reply_ms"](19200, timeout)
    assert healthy == pytest.approx(49.375)
    assert healthy_wire == pytest.approx(53 * 11 * 1000 / 19200)
    assert request_wire == pytest.approx(8 * 11 * 1000 / 19200)
    assert offline == pytest.approx(request_wire + timeout)
    assert (29 * healthy + offline) / 1000 == pytest.approx(sweep)
    guard = SAMPLE["silent_ms"](19200)
    assert SAMPLE["no_reply_ms"](19200, timeout, guard)[0] == pytest.approx(offline + guard)
