import runpy
from pathlib import Path

env = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                         "extensions/python_ethercat_deep_dive/example.py"))


def test_lrw_partial_contributions_and_ambiguous_mismatch():
    c = env["lrw_contribution"]
    expected = env["expected_wkc"](4, 2, 6)
    assert [c(False, False), c(True, False), c(False, True), c(True, True)] == [0, 1, 2, 3]
    assert expected == 26
    assert expected - c(True, False) == expected - c(True, True) + c(False, True) == 25
    assert expected - c(True, True) + c(True, False) == 24
    assert expected - c(True, True) == expected - c(True, False) - c(False, True) == 23
    compare = env["compare_wkc"]
    assert "另驗資料品質" in compare(expected, expected)
    for actual in (23, 24, 25, 27):
        assert "當筆資料不可用" in compare(expected, actual)
        assert "不能只靠總數定位" in compare(expected, actual)
