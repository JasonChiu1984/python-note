import math
import runpy
from pathlib import Path

env = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                         "extensions/python_iso50001_energy_reporting_tutorial/example.py"))


def test_prediction_band_includes_monthly_noise_and_correct_df():
    # At mean x=1: identical fitted values 2, residuals [-1, 2, -1].
    # n=3, SSE=6, df=1. Use t=1 to test geometry separately from t lookup.
    ci, pi = env["regression_intervals"]([0, 1, 2], [1, 4, 1], 1, 1)
    for actual, expected in zip(ci, (2 - math.sqrt(2), 2 + math.sqrt(2))):
        assert math.isclose(actual, expected)
    for actual, expected in zip(pi, (2 - math.sqrt(8), 2 + math.sqrt(8))):
        assert math.isclose(actual, expected)
    outside_ci, _ = env["regression_intervals"]([0, 1, 2], [1, 4, 1], 3, 1)
    assert outside_ci[1] - outside_ci[0] > ci[1] - ci[0]
