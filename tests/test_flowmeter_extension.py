import runpy
from pathlib import Path

example = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                            "extensions/python_flowmeter_calculation_tutorial/example.py"))
convert = example["ma_to_flow_dp"]


def test_dp_cutoff_preserves_five_percent_boundary():
    assert convert(4.04, 100, 0) == 5
    assert convert(4.039999999999999, 100) == 0
    assert convert(4.04, 100) == 0
    assert convert(4.040000000000001, 100) > 5
    assert convert(8, 100) == 50
