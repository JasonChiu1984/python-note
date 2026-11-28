import math
import runpy
from pathlib import Path

import pytest

repo_example = (Path(__file__).resolve().parents[1] /
                "extensions/python_ac_power_calculation_tutorial/example.py")
env = runpy.run_path(str(repo_example))
estimate = env["capacitor_kvar"]


def test_same_dpf_magnitude_different_reactive_direction():
    magnitude = 30 * math.tan(math.acos(0.85))
    assert magnitude == pytest.approx(18.59233015)
    assert estimate(30, magnitude, 0.95) == pytest.approx(8.73180699, abs=1e-6)
    assert estimate(30, -magnitude, 0.95) == 0


def test_zero_fundamental_q_does_not_compensate_harmonic_pf():
    p1 = 230 * 40 / 1000
    true_pf = p1 / (230 * math.sqrt(40**2 + 12**2 + 9**2) / 1000)
    assert true_pf < 0.95
    assert estimate(p1, 0.0, 0.95) == 0


def test_preserves_positive_q_sample_and_target_boundaries():
    total = sum(env["phase_power"](**phase) for phase in env["PHASES"].values())
    assert round(estimate(total.real, total.imag, 0.95), 1) == 39.0
    assert estimate(30, 2, 1) == 2
    with pytest.raises(ValueError):
        estimate(30, 2, 0)
