"""資料教材補充實驗：合成資料、暫存檔、完全離線。Python 3.11+。"""
import argparse
from io import BytesIO, StringIO
import json
from math import sqrt
from statistics import linear_regression, mean


def csv_contract():
    import pandas as pd

    raw = StringIO("point_id,kw\n001,0\nNA,\n002,N/A\n")
    df = pd.read_csv(raw, dtype={"point_id": "string", "kw": "Float64"},
                     keep_default_na=False, na_values={"kw": ["", "N/A"]})
    invalid = df["point_id"].isna() | df["point_id"].eq("")
    if invalid.any():
        raise ValueError("空白點號不可入帳")
    assert df["point_id"].tolist() == ["001", "NA", "002"]
    assert df["kw"].isna().tolist() == [False, True, True]
    assert df["kw"].sum(min_count=1) == 0
    assert pd.isna(df.loc[df["point_id"].eq("NA"), "kw"].sum(min_count=1))
    return {"ids": df["point_id"].tolist(), "zero": int(df["kw"].eq(0).sum()),
            "missing": int(df["kw"].isna().sum())}


def numpy_contract():
    import numpy as np

    readings = np.array([30000, 32000, 5], dtype=np.int16)
    step = np.array([10000, 1000, 0], dtype=np.int16)
    narrow = readings + step
    wide = np.add(readings, step, dtype=np.int64)
    reference = np.array([20000., np.nan, 0.])
    valid = np.isfinite(reference) & (reference > 0)
    normalized = np.full(reference.shape, np.nan, dtype=np.float64)
    with np.errstate(divide="raise", invalid="raise", over="raise"):
        np.divide(wide, reference, out=normalized, where=valid)
    assert narrow[0] == -25536 and wide[0] == 40000
    assert normalized[0] == 2 and np.isnan(normalized[1:]).all()
    return {"int16_result": narrow.tolist(), "int64_result": wide.tolist(),
            "normalized": [float(v) if ok else None for v, ok in zip(normalized, valid)]}


def pandas_join():
    import pandas as pd
    from pandas.errors import MergeError

    facts = pd.DataFrame({"id": ["A", "A", "B", "C", None],
                          "kwh": [12, 8, 5, 4, 99]})
    mapping = pd.DataFrame({"id": ["A", "B", None], "room": ["North", "South", "Unknown"]})
    without_key = facts.loc[facts["id"].isna()]
    source = facts.dropna(subset=["id"])
    dimension = mapping.dropna(subset=["id"])
    merged = source.merge(dimension, on="id", how="left",
                          validate="many_to_one", indicator=True)
    matched = merged.loc[merged["_merge"].eq("both"), "kwh"].sum()
    unmapped = merged.loc[merged["_merge"].eq("left_only"), "kwh"].sum()
    missing = without_key["kwh"].sum()
    assert matched + unmapped + missing == facts["kwh"].sum()
    try:
        source.merge(pd.concat([dimension, dimension.iloc[[0]]]), on="id",
                     validate="many_to_one")
    except MergeError:
        duplicate_blocked = True
    else:
        raise AssertionError("對照表重複鍵意外通過")
    return {"source_rows": len(facts), "joined_rows_excluding_null": len(merged),
            "matched_kwh": int(matched), "unmapped_kwh": int(unmapped),
            "missing_key_kwh": int(missing), "duplicate_blocked": duplicate_blocked}


def excel_contract():
    from openpyxl import Workbook, load_workbook

    wb = Workbook()
    sheet = wb.active
    sheet["A1"] = "001"
    sheet["B1"] = 12
    sheet["B2"] = 8
    sheet["B3"] = "=SUM(B1:B2)"  # 來自教材程式的可信公式
    sheet["C1"] = "=1+1"        # 來自外部欄位的合成字串
    sheet["C1"].data_type = "s"  # 明確存成文字，不交給試算表當公式
    sheet["D3"] = sum(sheet[f"B{r}"].value for r in (1, 2))  # Python 驗證值
    blob = BytesIO()
    wb.save(blob)
    wb.close()

    blob.seek(0)
    formulas = load_workbook(blob, data_only=False)
    original = formulas.active
    result = {"id": original["A1"].value, "formula": original["B3"].value,
              "untrusted_literal": original["C1"].value,
              "untrusted_type": original["C1"].data_type,
              "python_total": original["D3"].value}
    assert original["B3"].data_type == "f"
    formulas.close()
    blob.seek(0)
    cached = load_workbook(blob, data_only=True)
    result["formula_cached"] = cached.active["B3"].value
    cached.close()
    assert result["untrusted_type"] == "s" and result["untrusted_literal"] == "=1+1"
    assert result["formula_cached"] is None and result["python_total"] == 20
    return result


def regression_contract():
    # 模型只在訓練區配適；gap 模擬該筆標籤在預報時尚未到達。
    x = [1, 2, 3, 4, 5, 6, 7, 8]
    y = [12, 14, 16, 18, 20, 21, 21, 21]
    train, gap = 5, 1
    slope, intercept = linear_regression(x[:train], y[:train])
    test_x = x[train + gap:]
    truth = y[train + gap:]
    regression = [intercept + slope * v for v in test_x]
    baseline = [y[train - 1]] * len(truth)

    def score(prediction):
        error = [p - a for p, a in zip(prediction, truth, strict=True)]
        return {"mae": mean(abs(e) for e in error),
                "rmse": sqrt(mean(e * e for e in error)),
                "bias_prediction_minus_actual": mean(error)}

    result = {"test_actual": truth, "linear_prediction": regression,
              "persistence_prediction": baseline, "linear": score(regression),
              "persistence": score(baseline)}
    assert result["linear"]["mae"] == 4
    assert result["persistence"]["mae"] == 1
    return result


DEMOS = {"csv": csv_contract, "numpy": numpy_contract, "join": pandas_join,
         "excel": excel_contract, "regression": regression_contract}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=[*DEMOS, "all"])
    args = parser.parse_args()
    selected = DEMOS if args.case == "all" else {args.case: DEMOS[args.case]}
    print(json.dumps({key: func() for key, func in selected.items()},
                     ensure_ascii=False, allow_nan=False, indent=2))
