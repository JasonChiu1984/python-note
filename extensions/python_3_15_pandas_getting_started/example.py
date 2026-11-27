"""用 pandas 整理 BAS 趨勢資料：明確 dtype、缺值規則、15 分鐘重取樣、寬表轉換（需 pandas 3.x）。"""
from io import StringIO

import pandas as pd

RAW = """ts,point_id,value,quality
2026-11-20 08:00:05,001,22.4,good
2026-11-20 08:04:58,001,22.6,good
2026-11-20 08:09:40,001,,comm_fail
2026-11-20 08:15:02,001,23.1,good
2026-11-20 08:00:10,NA,12.8,good
2026-11-20 08:05:12,NA,12.9,good
2026-11-20 08:15:30,NA,13.4,good
2026-11-20 08:20:00,NA,13.3,good
"""

if __name__ == "__main__":
    print("pandas", pd.__version__.split(".")[0] + ".x")
    df = pd.read_csv(StringIO(RAW), dtype={"point_id": "string", "value": "Float64", "quality": "category"},
                     keep_default_na=False, na_values={"value": [""]}, parse_dates=["ts"])
    print(df.dtypes.to_string())
    print(f"點位代碼：{df['point_id'].unique().tolist()}（001 保留前導零，NA 是代碼不是缺值）")

    names = {"001": "AHU1_SAT", "NA": "CHW_SUPPLY"}
    df["point"] = df["point_id"].map(names)
    good = df[df["quality"] == "good"]
    wide = (good.set_index("ts").groupby("point")["value"]
            .resample("15min").agg(["mean", "count"]).unstack(level=0))
    wide.columns = [f"{p}_{stat}" for stat, p in wide.columns]
    print(wide.round(2).to_string())

    coverage = good.groupby("point").size() / df.groupby("point").size()
    print("有效資料比例：", coverage.round(2).to_dict())
    print("comm_fail 筆數：", int((df["quality"] == "comm_fail").sum()))
