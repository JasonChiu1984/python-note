"""冷卻塔散熱與冷凍廠能效的離線算例；僅用 Python 標準函式庫。"""
import math
import sys
import unittest

KW_PER_RT = 3.516853
RHO = 1000.0        # kg/m³，合成純水近似
CP = 4.186          # kJ/(kg·K)
G = 9.81           # m/s²


def nonnegative(*values):
    if not all(math.isfinite(v) and v >= 0 for v in values):
        raise ValueError("各功率、流量及時間必須為有限非負數")


def tower_heat_kw(flow_m3h, incoming_hot_c, leaving_cold_c, entering_wetbulb_c):
    """回傳（水側散熱 kW、Range K、Approach K）；量測點為開式蒸發塔。"""
    nonnegative(flow_m3h)
    if not all(math.isfinite(v) for v in (incoming_hot_c, leaving_cold_c, entering_wetbulb_c)):
        raise ValueError("溫度須為有限數")
    span = incoming_hot_c - leaving_cold_c
    approach = leaving_cold_c - entering_wetbulb_c
    if span < 0 or approach < 0:
        raise ValueError("冷卻塔溫度關係異常；檢查測點、同步與工況")
    return RHO * flow_m3h / 3600 * CP * span, span, approach


def pump_input_kw(flow_m3h, head_m, efficiency):
    """把全部泵組損失合在效率內；有實測輸入真功率就優先用實測。"""
    nonnegative(flow_m3h, head_m)
    if not 0 < efficiency <= 1:
        raise ValueError("線到水效率須大於 0 且不超過 1")
    return RHO * G * (flow_m3h / 3600) * head_m / (1000 * efficiency)


def ratios(windows):
    """窗資料（h, 散熱kW, 蒸發器冷量kW, 塔風機kW, 冷凝泵kW, 壓縮機kW, 冰水泵kW）。"""
    total = [0.0] * 6
    for hours, rejected, evap, fan, condenser_pump, compressor, chilled_pump in windows:
        nonnegative(hours, rejected, evap, fan, condenser_pump, compressor, chilled_pump)
        if hours == 0:
            raise ValueError("區間長度不可為零")
        for i, x in enumerate((rejected / KW_PER_RT, evap / KW_PER_RT, fan,
                               condenser_pump, compressor, chilled_pump)):
            total[i] += x * hours
    rejected_rth, evap_rth, fan_kwh, pump_kwh, compressor_kwh, chilled_kwh = total
    plant = fan_kwh + pump_kwh + compressor_kwh + chilled_kwh
    return {
        "rejected_rt_h": rejected_rth, "evaporator_rt_h": evap_rth,
        "fan_kwh": fan_kwh, "fan_and_condenser_pump_kwh": fan_kwh + pump_kwh,
        "plant_kwh": plant,
        "fan_kw_per_rejected_rt": fan_kwh / rejected_rth if rejected_rth else None,
        "fan_pump_kw_per_rejected_rt": (fan_kwh + pump_kwh) / rejected_rth if rejected_rth else None,
        "plant_kw_per_evaporator_rt": plant / evap_rth if evap_rth else None,
    }


def demo():
    rejected, span, approach = tower_heat_kw(216, 35, 30, 26)
    pump = pump_input_kw(216, 18, 0.72)
    rows = [(0.5, rejected, 1015, fan, pump, 230, 10) for fan in (22, 12)]
    return {"range_k": span, "approach_k": approach, "tower_heat_kw": rejected,
            "condenser_pump_kw_est": pump, **ratios(rows)}


class Tests(unittest.TestCase):
    def test_case(self):
        out = demo()
        self.assertAlmostEqual(out["tower_heat_kw"], 1255.8)
        self.assertAlmostEqual(out["condenser_pump_kw_est"], 14.715)
        self.assertAlmostEqual(out["fan_kwh"], 17)
        self.assertAlmostEqual(out["plant_kwh"], 271.715)

    def test_weighting(self):
        out = ratios([(1, KW_PER_RT, KW_PER_RT, 2, 0, 0, 0),
                      (1, 3 * KW_PER_RT, 3 * KW_PER_RT, 3, 0, 0, 0)])
        self.assertAlmostEqual(out["fan_kw_per_rejected_rt"], 1.25)

    def test_invalid_and_missing(self):
        with self.assertRaises(ValueError):
            tower_heat_kw(216, 35, 30, 31)
        with self.assertRaises(ValueError):
            pump_input_kw(5, 3, 0)
        self.assertIsNone(ratios([(1, 0, 0, 1, 0, 0, 0)])["plant_kw_per_evaporator_rt"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        unittest.main(argv=[sys.argv[0]])
    else:
        for key, value in demo().items():
            print(f"{key}: {value:.4f}")
