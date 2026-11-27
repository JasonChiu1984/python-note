"""Offline synthetic telemetry, pandas 2.2+; no device I/O."""
from __future__ import annotations

import argparse
import io
import json
import platform
import statistics
import time
import unittest

import numpy as np
import pandas as pd

CSV = """device_id,event_at,kw,status
001,2026-01-01T00:00:00Z,0,GOOD
001,2026-01-01T00:15:00Z,,MISSING
001,2026-01-01T00:30:00Z,4,GOOD
002,2026-01-01T00:15:00Z,2,GOOD
"""


def read_telemetry(text: str) -> pd.DataFrame:
    x = pd.read_csv(io.StringIO(text), dtype={
        "device_id": "string", "event_at": "string", "kw": "Float64", "status": "string",
    }, keep_default_na=False, na_values={"kw": [""]})
    if list(x.columns) != ["device_id", "event_at", "kw", "status"]:
        raise ValueError("unexpected schema")
    if not x["device_id"].str.fullmatch(r"\d{3}", na=False).all():
        raise ValueError("device_id must be exactly 3 digits")
    if not x["event_at"].str.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", na=False).all():
        raise ValueError("expected timestamps with explicit UTC Z")
    x["event_at"] = pd.to_datetime(x["event_at"], utc=True, errors="raise")
    if x.duplicated(["device_id", "event_at"]).any():
        raise ValueError("duplicate event key")
    if not x["status"].isin(["GOOD", "MISSING"]).all():
        raise ValueError("unknown status")
    if not x["kw"].notna().eq(x["status"].eq("GOOD")).all():
        raise ValueError("status and value disagree")
    if not np.isfinite(x["kw"].dropna().to_numpy(dtype=float)).all() or x["kw"].lt(0).fillna(False).any():
        raise ValueError("invalid load")
    return x


def attach_assets(events: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    for label, frame in [("events", events), ("assets", assets)]:
        if frame["device_id"].isna().any() or frame["device_id"].eq("").any():
            raise ValueError(f"{label} contains null/empty join keys")
    out = events.merge(assets, on="device_id", how="left", validate="many_to_one", indicator=True)
    if not out["_merge"].eq("both").all():
        raise ValueError("unregistered device")
    return out.drop(columns="_merge")


def window(hourly_input: pd.DataFrame) -> pd.DataFrame:
    # 每筆代表已知 15 分鐘區間的平均 kW；缺值保持未知。
    if hourly_input["event_at"].ne(hourly_input["event_at"].dt.floor("15min")).any():
        raise ValueError("timestamps must align to 15-minute boundary")
    x = hourly_input.assign(kwh=hourly_input["kw"] * 0.25)
    g = x.groupby(["device_id", pd.Grouper(key="event_at", freq="h",
                    origin="start_day", closed="left", label="left")], observed=True)["kwh"]
    out = pd.concat([g.size().rename("received"), g.count().rename("valid"),
                     g.sum(min_count=1).rename("known_kwh")], axis=1)
    out["coverage"] = out["valid"] / 4
    out["complete_kwh"] = out["known_kwh"].where(out["valid"].eq(4))
    return out


def align_calibration(events: pd.DataFrame, log: pd.DataFrame) -> pd.DataFrame:
    if not events["event_at"].notna().all() or not log["available_at"].notna().all():
        raise ValueError("unknown availability")
    if log.duplicated(["device_id", "available_at"]).any():
        raise ValueError("ambiguous calibration tie")
    return pd.merge_asof(events.sort_values("event_at"), log.sort_values("available_at"),
                         by="device_id", left_on="event_at", right_on="available_at",
                         direction="backward", tolerance=pd.Timedelta("1h"),
                         allow_exact_matches=False)


def calibration() -> pd.DataFrame:
    return pd.DataFrame({"device_id": pd.Series(["001", "001"], dtype="string"),
                         "available_at": pd.to_datetime(["2025-12-31T23:55:00Z",
                                                         "2026-01-01T00:16:00Z"], utc=True),
                         "offset": [0.2, 3.0]})


def benchmark(n: int = 20_000, repeats: int = 5) -> dict:
    if not 1 <= n <= 100_000 or not 3 <= repeats <= 20:
        raise ValueError("out-of-range size or repetitions")
    source = pd.DataFrame({"kw": np.arange(n, dtype=np.int64) % 100})
    def vectorized() -> pd.Series:
        return source["kw"] * 2 + 1
    def callback() -> pd.Series:
        return source["kw"].map(lambda k: k * 2 + 1)
    jobs = {"vectorized": vectorized, "callback": callback}
    pd.testing.assert_series_equal(vectorized(), callback())
    times: dict[str, list[float]] = {k: [] for k in jobs}
    for i in range(repeats):
        for name in list(jobs)[::(-1 if i % 2 else 1)]:
            start = time.perf_counter_ns()
            jobs[name]()
            times[name].append((time.perf_counter_ns() - start) / 1e6)
    return {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
            "rows": n, "repeats": repeats, "input_deep_bytes": int(source.memory_usage(deep=True).sum()),
            "times_ms": times, "median_ms": {k: statistics.median(v) for k, v in times.items()}}


class Tests(unittest.TestCase):
    def setUp(self):
        self.x = read_telemetry(CSV)
        self.assets = pd.DataFrame({"device_id": pd.Series(["001", "002"], dtype="string"),
                                    "building": ["A", "B"]})

    def test_dtypes_and_na(self):
        self.assertEqual(self.x["device_id"].tolist(), ["001", "001", "001", "002"])
        self.assertEqual(str(self.x["kw"].dtype), "Float64")
        self.assertTrue(pd.isna(self.x["kw"].iloc[1]))
        self.assertEqual(self.x["kw"].iloc[0], 0)

    def test_input_rejected(self):
        for invalid in [CSV + CSV.splitlines()[1] + "\n", CSV.replace("0,GOOD", ",GOOD"),
                        CSV.replace("00:00:00Z", "00:00:00"), CSV.replace("4,GOOD", "inf,GOOD")]:
            with self.assertRaises(ValueError):
                read_telemetry(invalid)

    def test_join_contract(self):
        self.assertEqual(len(attach_assets(self.x, self.assets)), len(self.x))
        with self.assertRaises(pd.errors.MergeError):
            attach_assets(self.x, pd.concat([self.assets, self.assets.iloc[:1]]))
        with self.assertRaises(ValueError):
            attach_assets(self.x, self.assets.iloc[:1])
        with self.assertRaises(ValueError):
            attach_assets(self.x, self.assets.assign(device_id=pd.NA))

    def test_window_unknown_is_not_zero(self):
        a = window(self.x).loc["001"].iloc[0]
        self.assertEqual((a["received"], a["valid"], a["coverage"], a["known_kwh"]), (3, 2, .5, 1.0))
        self.assertTrue(pd.isna(a["complete_kwh"]))
        with self.assertRaises(ValueError):
            window(self.x.assign(event_at=self.x["event_at"] + pd.Timedelta("1min")))

    def test_wholly_missing_bucket(self):
        result = window(self.x.iloc[[1]]).iloc[0]
        self.assertEqual((result["received"], result["valid"]), (1, 0))
        self.assertTrue(pd.isna(result["known_kwh"]))

    def test_no_future(self):
        aligned = align_calibration(self.x, calibration())
        early = aligned.loc[(aligned["device_id"] == "001") &
                            (aligned["event_at"] == pd.Timestamp("2026-01-01T00:15:00Z"))]
        self.assertEqual(early["offset"].iloc[0], .2)
        matched = aligned.loc[aligned["available_at"].notna()]
        self.assertTrue((matched["available_at"] < matched["event_at"]).all())

    def test_benchmark_structure(self):
        info = benchmark(100, 3)
        self.assertEqual([len(v) for v in info["times_ms"].values()], [3, 3])
        self.assertGreater(info["input_deep_bytes"], 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["demo", "test", "bench"])
    args = parser.parse_args()
    if args.mode == "test":
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if args.mode == "bench":
        print(json.dumps(benchmark(), ensure_ascii=False, indent=2, allow_nan=False))
    else:
        x = read_telemetry(CSV)
        print(window(x).to_string())
        print(align_calibration(x, calibration())[["device_id", "event_at", "offset"]].to_string(index=False))


if __name__ == "__main__":
    main()
