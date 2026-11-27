"""年度範疇一、二彙總與碳費試算（教學模型）。

- 範疇二採 114 年度「產業電力排碳係數」0.466 kgCO2e/kWh（經濟部能源署公告）。
- 燃料排放係數為教學假設值，正式盤查請改用環境部「溫室氣體排放係數管理表」對應年度版本。
- 碳費以一般費率每公噸 300 元、年排放量扣除 25,000 公噸後計費（碳費收費辦法）。
"""
from decimal import Decimal as D, ROUND_HALF_UP

ELECTRICITY_FACTOR = D("0.466")            # kgCO2e/kWh，114 年度產業係數
FUEL_FACTORS = {                           # kgCO2e/單位，教學假設值
    "natural_gas_m3": D("2.09"),
    "diesel_l": D("2.61"),
}

# 某廠 12 個月的活動量：電力 kWh、天然氣 m3、柴油 L（緊急發電機）
MONTHLY = [
    # (月, 電力 kWh, 天然氣 m3, 柴油 L)
    (1, 3_850_000, 182_000, 900), (2, 3_420_000, 171_000, 0),
    (3, 3_910_000, 176_500, 1_200), (4, 4_020_000, 160_200, 0),
    (5, 4_480_000, 151_000, 0), (6, 4_960_000, 140_800, 2_400),
    (7, 5_210_000, 138_400, 0), (8, 5_260_000, 139_900, 0),
    (9, 4_870_000, 145_700, 1_100), (10, 4_390_000, 156_300, 0),
    (11, 4_010_000, 168_800, 0), (12, 3_930_000, 179_600, 800),
]
GREEN_POWER_KWH = 6_000_000                # 當年度取得並註銷的再生能源憑證對應電量


def t(kg: D) -> D:
    return (kg / 1000).quantize(D("0.01"), ROUND_HALF_UP)


def annual_totals():
    kwh = sum(D(m[1]) for m in MONTHLY)
    gas = sum(D(m[2]) for m in MONTHLY)
    diesel = sum(D(m[3]) for m in MONTHLY)
    scope1 = gas * FUEL_FACTORS["natural_gas_m3"] + diesel * FUEL_FACTORS["diesel_l"]
    scope2_location = kwh * ELECTRICITY_FACTOR
    scope2_market = (kwh - GREEN_POWER_KWH) * ELECTRICITY_FACTOR
    return kwh, gas, diesel, t(scope1), t(scope2_location), t(scope2_market)


def carbon_fee(total_t: D, rate=D(300), threshold=D(25_000)):
    chargeable = max(D(0), total_t - threshold)
    return chargeable, (chargeable * rate).quantize(D("1"), ROUND_HALF_UP)


if __name__ == "__main__":
    kwh, gas, diesel, s1, s2_loc, s2_mkt = annual_totals()
    print(f"年用電 {kwh:,} kWh、天然氣 {gas:,} m3、柴油 {diesel:,} L")
    print(f"範疇一：{s1:,} tCO2e")
    print(f"範疇二（地區基礎，0.466）：{s2_loc:,} tCO2e")
    print(f"範疇二（市場基礎，扣除 {GREEN_POWER_KWH:,} kWh 憑證）：{s2_mkt:,} tCO2e")
    total = s1 + s2_loc
    print(f"範疇一＋二（地區基礎）：{total:,} tCO2e")
    chargeable, fee = carbon_fee(total)
    print(f"若適用碳費一般費率：計費排放量 {chargeable:,} t，碳費 NT$ {fee:,}")
    peak = max(MONTHLY, key=lambda m: m[1])
    print(f"用電最高月份：{peak[0]} 月，{peak[1]:,} kWh，"
          f"占全年 {(D(peak[1]) / kwh * 100).quantize(D('0.1'))}%")
