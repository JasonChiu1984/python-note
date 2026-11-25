"""流量計計算：乾式離線實驗（Python 3.11+，純標準函式庫）。

    python3 python_flowmeter_calculation_lab.py
    python3 python_flowmeter_calculation_lab.py --self-test

全部使用合成資料，不連線現場設備。輸出不是校正、驗收或控制指令。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from typing import Iterable
import unittest


# 每一單位等於多少 m³/s；換算先換成共同單位，再轉輸出。
TO_M3_S = {"m³/s": 1.0, "m³/h": 1 / 3_600, "L/min": 1 / 60_000}


def finite(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} 必須為有限數值")
    return value


def positive(name: str, value: float) -> float:
    if finite(name, value) <= 0:
        raise ValueError(f"{name} 必須大於零")
    return value


def convert_flow(value: float, source: str, target: str) -> float:
    if source not in TO_M3_S or target not in TO_M3_S:
        raise ValueError("單位只接受 m³/s、m³/h、L/min")
    return finite("換算流量", finite("流量", value) * TO_M3_S[source] / TO_M3_S[target])


def pipe_flow(inside_mm: float, mean_m_s: float, *, bidirectional: bool = False) -> float:
    """回傳 m³/s。適用已滿管、已知代表性截面平均軸向速度的圓管。"""
    diameter_m = positive("實際內徑 mm", inside_mm) / 1000
    if finite("截面平均速度", mean_m_s) < 0 and not bidirectional:
        raise ValueError("單向模式不將負值變成正值；請檢查方向/訊號")
    area = math.pi * (diameter_m / 2) * (diameter_m / 2)
    return finite("體積流量", area * mean_m_s)


def pulse_window(delta_pulses: int, seconds: float, pulses_per_litre: float) -> tuple[float, float]:
    """回傳 (此窗總量 L, 此窗平均流量 L/min)，K 的單位必須是 pulse/L。"""
    if not isinstance(delta_pulses, int) or isinstance(delta_pulses, bool) or delta_pulses < 0:
        raise ValueError("脈衝增量須是非負整數；不得把 reset/回捲當普通差值")
    volume_l = finite("脈衝體積", delta_pulses / positive("K pulse/L", pulses_per_litre))
    return volume_l, finite("脈衝流量", volume_l / positive("計數窗秒數", seconds) * 60)


@dataclass(frozen=True)
class Reading:
    value_m3_h: float | None
    quality: str


def dp_to_flow(
    dp_kpa: float, *, fs_dp_kpa: float, fs_flow_m3_h: float, cutoff_kpa: float = 0,
) -> Reading:
    """只處理尚未平方根萃取、零起點的單向 ΔP，簡化為固定密度。"""
    positive("差壓滿量程 kPa", fs_dp_kpa)
    positive("流量滿量程 m³/h", fs_flow_m3_h)
    if not 0 <= finite("低流量切除 kPa", cutoff_kpa) < fs_dp_kpa:
        raise ValueError("低流量切除必須非負且小於差壓滿量程")
    if not math.isfinite(dp_kpa):
        return Reading(None, "invalid")
    if dp_kpa < 0:
        return Reading(None, "negative_dp")
    if dp_kpa > fs_dp_kpa:
        return Reading(None, "over_range")
    if dp_kpa < cutoff_kpa:
        return Reading(0.0, "low_flow_cutoff")
    return Reading(fs_flow_m3_h * math.sqrt(dp_kpa / fs_dp_kpa), "ok")


def decode_ma(
    ma: float, *, mode: str, max_flow_m3_h: float, min_flow_m3_h: float = 0,
    fs_dp_kpa: float | None = None, cutoff_kpa: float = 0,
) -> Reading:
    """mode=linear_flow 為已轉成流量；mode=raw_dp 為 4–20 mA 線性代表原始差壓。"""
    if mode not in {"linear_flow", "raw_dp"}:
        raise ValueError("mode 必須明確指定 linear_flow 或 raw_dp")
    if not 0 <= finite("流量下量程", min_flow_m3_h) < positive("流量上量程", max_flow_m3_h):
        raise ValueError("需有 0 <= 下量程 < 上量程")
    if mode == "raw_dp":
        if min_flow_m3_h != 0 or fs_dp_kpa is None:
            raise ValueError("教材的 raw_dp 只支援零起點，且必須提供差壓滿量程")
        positive("差壓滿量程 kPa", fs_dp_kpa)
        if not 0 <= finite("低流量切除 kPa", cutoff_kpa) < fs_dp_kpa:
            raise ValueError("低流量切除必須非負且小於差壓滿量程")
    elif fs_dp_kpa is not None or cutoff_kpa != 0:
        raise ValueError("linear_flow 不應設定差壓參數，避免重複轉換")
    if not math.isfinite(ma):
        return Reading(None, "invalid")
    if ma < 4:
        return Reading(None, "under_range")
    if ma > 20:
        return Reading(None, "over_range")

    fraction = (ma - 4) / 16
    if mode == "linear_flow":
        return Reading(min_flow_m3_h + fraction * (max_flow_m3_h - min_flow_m3_h), "ok")
    assert fs_dp_kpa is not None
    return dp_to_flow(fraction * fs_dp_kpa, fs_dp_kpa=fs_dp_kpa,
                      fs_flow_m3_h=max_flow_m3_h, cutoff_kpa=cutoff_kpa)


@dataclass(frozen=True)
class TimedFlow:
    t_seconds: float
    flow_m3_h: float | None
    quality: str = "ok"


def integrate_total(
    samples: Iterable[TimedFlow], *, max_gap_s: float, bidirectional: bool = False,
) -> dict:
    """梯形積分，只跨連續且兩端有效的樣本。時間為同一基準的秒數。"""
    positive("最大允許採樣間距", max_gap_s)
    last: TimedFlow | None = None
    increments: list[float] = []
    elapsed = valid = 0.0
    skipped = 0

    def is_usable(s: TimedFlow) -> bool:
        q = s.flow_m3_h
        # "low_flow_cutoff" 不是經測得的零；本教材不以它積分。
        return s.quality == "ok" and q is not None and math.isfinite(q) and (q >= 0 or bidirectional)

    for sample in samples:
        finite("採樣時間", sample.t_seconds)
        if last is not None:
            dt = finite("時間差", sample.t_seconds - last.t_seconds)
            if dt <= 0:
                raise ValueError("採樣時間須嚴格遞增，不可先靜默重排或保留重複資料")
            elapsed += dt
            if dt <= max_gap_s and is_usable(last) and is_usable(sample):
                assert last.flow_m3_h is not None and sample.flow_m3_h is not None
                mean_m3_h = last.flow_m3_h / 2 + sample.flow_m3_h / 2
                increments.append(finite("分段總量", mean_m3_h * (dt / 3600)))
                valid += dt
            else:
                skipped += 1
        last = sample

    return {
        "total_m3_valid_segments": math.fsum(increments) if increments else None,
        "elapsed_s_between_first_last": elapsed,
        "covered_s": valid,
        "coverage": valid / elapsed if elapsed else None,
        "valid_segments": len(increments),
        "skipped_segments": skipped,
    }


def compare_meters(a_ref_m3_h: float, b_m3_h: float) -> dict:
    """以 A 作比較基準（不是標準器），兩值必須已同時且由同一流路量測。"""
    positive("比較基準 A", a_ref_m3_h)
    if finite("比較值 B", b_m3_h) < 0:
        raise ValueError("單向比較不接受負值")
    delta = b_m3_h - a_ref_m3_h
    return {
        "delta_m3_h": delta,
        "b_vs_a_pct": finite("以 A 為分母的差異", delta / a_ref_m3_h * 100),
        "symmetric_difference_pct": abs(delta) / (a_ref_m3_h / 2 + b_m3_h / 2) * 100,
    }


def demo() -> dict:
    q = pipe_flow(250, 1.2)
    lit, lmin = pulse_window(1500, 30, 200)
    samples = [TimedFlow(0, 60), TimedFlow(60, 120),
               TimedFlow(120, 80), TimedFlow(180, None, "stale"), TimedFlow(300, 90)]
    return {
        "source": "synthetic offline values",
        "pipe": {unit: round(convert_flow(q, "m³/s", unit), 6) for unit in TO_M3_S},
        "pulse": {"volume_L": lit, "average_L_min": lmin},
        "8_mA": {
            "linear_flow": asdict(decode_ma(8, mode="linear_flow", max_flow_m3_h=100)),
            "raw_dp": asdict(decode_ma(8, mode="raw_dp", max_flow_m3_h=100, fs_dp_kpa=100)),
        },
        "integration": integrate_total(samples, max_gap_s=60),
        "meter_comparison_100_vs_140": compare_meters(100, 140),
    }


class FlowTests(unittest.TestCase):
    def test_units_round_trip(self):
        self.assertAlmostEqual(convert_flow(1000, "L/min", "m³/h"), 60)
        self.assertAlmostEqual(convert_flow(60, "m³/h", "m³/s"), 1 / 60)
        self.assertAlmostEqual(convert_flow(1 / 60, "m³/s", "L/min"), 1000)
        with self.assertRaises(ValueError):
            convert_flow(1, "m³", "m³/h")

    def test_pipe_and_reverse(self):
        self.assertAlmostEqual(pipe_flow(250, 1.2), 0.05890486225480862)
        self.assertEqual(pipe_flow(250, 0), 0)
        self.assertAlmostEqual(pipe_flow(250, -1.2, bidirectional=True), -pipe_flow(250, 1.2))
        for d, v in [(0, 1), (250, -1), (250, float("nan"))]:
            with self.assertRaises(ValueError):
                pipe_flow(d, v)

    def test_pulse(self):
        self.assertEqual(pulse_window(1500, 30, 200), (7.5, 15))
        self.assertEqual(pulse_window(0, 30, 200), (0, 0))
        for args in [(-1, 10, 200), (1, 0, 200), (1, 10, 0), (1.5, 10, 200)]:
            with self.assertRaises(ValueError):
                pulse_window(*args)

    def test_signal_modes(self):
        self.assertEqual(decode_ma(8, mode="linear_flow", max_flow_m3_h=100), Reading(25, "ok"))
        self.assertEqual(decode_ma(8, mode="raw_dp", max_flow_m3_h=100, fs_dp_kpa=100), Reading(50, "ok"))
        self.assertEqual(decode_ma(4, mode="linear_flow", min_flow_m3_h=10, max_flow_m3_h=100), Reading(10, "ok"))
        self.assertEqual(decode_ma(20, mode="raw_dp", max_flow_m3_h=100, fs_dp_kpa=100), Reading(100, "ok"))
        with self.assertRaises(ValueError):
            decode_ma(8, mode="linear_flow", max_flow_m3_h=100, fs_dp_kpa=100)

    def test_quality_flags(self):
        for ma, quality in [(3.9, "under_range"), (20.1, "over_range"), (float("inf"), "invalid")]:
            self.assertEqual(decode_ma(ma, mode="linear_flow", max_flow_m3_h=100), Reading(None, quality))
        for dp, result in [(-0.1, Reading(None, "negative_dp")), (101, Reading(None, "over_range")),
                           (0.4, Reading(0, "low_flow_cutoff"))]:
            self.assertEqual(dp_to_flow(dp, fs_dp_kpa=100, fs_flow_m3_h=100, cutoff_kpa=.5), result)
        self.assertGreater(dp_to_flow(.5, fs_dp_kpa=100, fs_flow_m3_h=100, cutoff_kpa=.5).value_m3_h, 0)

    def test_trapezoid_and_invalid_gaps(self):
        r = demo()["integration"]
        self.assertAlmostEqual(r["total_m3_valid_segments"], 19/6)
        self.assertEqual((r["covered_s"], r["coverage"], r["skipped_segments"]), (120, .4, 2))
        self.assertIsNone(integrate_total([TimedFlow(0, 60), TimedFlow(61, 60)], max_gap_s=60)["total_m3_valid_segments"])
        self.assertIsNone(integrate_total([TimedFlow(0, 0), TimedFlow(60, 0, "low_flow_cutoff")], max_gap_s=60)["total_m3_valid_segments"])
        self.assertEqual(integrate_total([TimedFlow(0, 0), TimedFlow(60, 0)], max_gap_s=60)["total_m3_valid_segments"], 0)

    def test_time_order_and_empty(self):
        for t in (0, -1):
            with self.assertRaises(ValueError):
                integrate_total([TimedFlow(0, 60), TimedFlow(t, 60)], max_gap_s=60)
        self.assertIsNone(integrate_total([], max_gap_s=60)["coverage"])

    def test_compare_reference(self):
        r = compare_meters(100, 140)
        self.assertEqual((r["delta_m3_h"], r["b_vs_a_pct"]), (40, 40))
        self.assertAlmostEqual(r["symmetric_difference_pct"], 100/3)
        with self.assertRaises(ValueError):
            compare_meters(0, 140)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--self-test", action="store_true")
    if p.parse_args().self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(FlowTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    print(json.dumps(demo(), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
