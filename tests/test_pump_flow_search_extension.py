from pathlib import Path
import runpy

import pytest


P = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       "extensions/python_water_pump_calculation_tutorial/example.py"))


def test_reachable_open_loop_point():
    k = 18 / 150**2
    full, _ = P["operating_point"](1, 12, k)
    n = P["speed_for_flow"](full * 0.6, 12, k)
    q, h = P["operating_point"](n, 12, k)
    assert n == pytest.approx(0.7367883976)
    assert q == pytest.approx(full * 0.6)
    assert P["electric_kw"](q, h) == pytest.approx(4.53890449)
    assert P["speed_for_flow"](full, 12, k) == 1


def test_checks_both_bounds():
    k = 30 / 150**2
    low, _ = P["operating_point"](0.2, 0, k)
    assert P["speed_for_flow"](low, 0, k) == pytest.approx(0.2)
    with pytest.raises(ValueError, match="超出模型可達"):
        P["speed_for_flow"](low / 2, 0, k)
    with pytest.raises(ValueError, match="超出模型可達"):
        P["speed_for_flow"](130, 12, 18 / 150**2)


def test_invalid_targets_do_not_return_a_speed():
    for args in ((0, 0, 0.001), (1, -1, 0.001), (1, 5, -0.001), (float("nan"), 5, 0.001)):
        with pytest.raises(ValueError, match="本模型要求"):
            P["speed_for_flow"](*args)


def test_efficiency_at_fixed_sixty_percent_flow():
    k = 22 / 150**2
    full, _ = P["operating_point"](1, 8, k)
    n = P["speed_for_flow"](full * 0.6, 8, k)
    q, h = P["operating_point"](n, 8, k)
    assert n == pytest.approx(0.6941936055)
    assert P["electric_kw"](q, h) * 0.72 / 0.62 == pytest.approx(4.44680467)
