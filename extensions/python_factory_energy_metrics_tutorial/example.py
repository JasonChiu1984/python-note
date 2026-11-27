"""單位良品能耗與分攤：主電表與分電表對帳、公用設施依量測分攤、良品數為分母（標準函式庫 Decimal）。"""
from decimal import Decimal as D, ROUND_HALF_UP

MAIN_KWH = D("186400")                     # 台電主電表（月）
SUB = {"產線A": D("72300"), "產線B": D("58900"), "空壓": D("21800"), "冰水": D("27600")}
COMPRESSED_AIR_SHARE = {"產線A": D("0.62"), "產線B": D("0.38")}    # 依各線流量計
CHW_SHARE = {"產線A": D("0.45"), "產線B": D("0.55")}               # 依各線冰水冷量計
GOOD = {"產線A": 48_200, "產線B": 31_500}
TOTAL = {"產線A": 50_100, "產線B": 31_900}


def q(x, p="0.01"):
    return x.quantize(D(p), ROUND_HALF_UP)


if __name__ == "__main__":
    unmetered = MAIN_KWH - sum(SUB.values())
    print(f"主電表 {MAIN_KWH:,} kWh，分表合計 {sum(SUB.values()):,} kWh，未計量 {unmetered:,} kWh"
          f"（{q(unmetered / MAIN_KWH * 100, '0.1')}%）")
    if unmetered / MAIN_KWH > D("0.05"):
        print("  ⚠ 未計量超過 5%，先查照明、辦公與分表倍率，再談分攤")
    for line in ("產線A", "產線B"):
        kwh = SUB[line] + SUB["空壓"] * COMPRESSED_AIR_SHARE[line] + SUB["冰水"] * CHW_SHARE[line]
        per_good = kwh / GOOD[line]
        per_total = kwh / TOTAL[line]
        yield_rate = D(GOOD[line]) / TOTAL[line]
        print(f"{line}：分攤後 {q(kwh, '1'):,} kWh，良率 {q(yield_rate * 100, '0.1')}%，"
              f"每件良品 {q(per_good, '0.001')} kWh（以總產出計 {q(per_total, '0.001')}）")
    print("良率越低，「每件良品」與「每件產出」的差距越大；改善良率本身就是節能。")
