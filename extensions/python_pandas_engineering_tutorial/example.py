"""pandas 工程化：merge 驗證關聯、對齊時間戳（merge_asof）、檢查合併前後筆數（需 pandas 3.x）。"""
import pandas as pd

readings = pd.DataFrame({
    "ts": pd.to_datetime(["2026-11-20 08:00:03", "2026-11-20 08:00:07", "2026-11-20 08:00:12",
                          "2026-11-20 08:00:03", "2026-11-20 08:00:09"]),
    "point": ["SAT", "SAT", "SAT", "KW", "KW"],
    "value": [22.4, 22.5, 22.7, 128.0, 131.5],
})
points = pd.DataFrame({"point": ["SAT", "KW", "KW"], "unit": ["degC", "kW", "kW"],
                       "ahu": ["AHU-01", "AHU-01", "AHU-02"]})          # 點位表中 KW 重複了
setpoints = pd.DataFrame({"ts": pd.to_datetime(["2026-11-20 08:00:00", "2026-11-20 08:00:10"]),
                          "sat_sp": [22.0, 23.0]})

if __name__ == "__main__":
    try:
        readings.merge(points, on="point", how="left", validate="many_to_one")
    except pd.errors.MergeError as e:
        print("merge 驗證失敗：", str(e).splitlines()[0])
    dup = points[points.duplicated("point", keep=False)]
    print("點位表重複鍵：", dup.to_dict("records"))
    clean = points.drop_duplicates("point", keep="first")
    merged = readings.merge(clean, on="point", how="left", validate="many_to_one")
    print(f"合併前 {len(readings)} 筆、合併後 {len(merged)} 筆（必須相同）")
    sat = readings[readings["point"] == "SAT"].sort_values("ts")
    aligned = pd.merge_asof(sat, setpoints.sort_values("ts"), on="ts", direction="backward")
    aligned["error"] = (aligned["value"] - aligned["sat_sp"]).round(2)
    print(aligned[["ts", "value", "sat_sp", "error"]].to_string(index=False))
