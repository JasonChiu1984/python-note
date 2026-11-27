"""從 1 分鐘電力取樣計算 15 分鐘需量、契約超約與尖峰比例（教學模型，非帳單引擎）。

情境：機房配電盤的電力表每分鐘回傳一筆有效功率 kW（例如經 Modbus 讀回）。
台電以 15 分鐘平均功率計需量；本例找出當日最高需量並判斷是否超過契約容量。
超約部分的加收倍數（10% 以內 2 倍、超過 10% 的部分 3 倍）以參數傳入，實際以台電電價表為準。
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta

D = Decimal


def synthetic_samples(start: datetime) -> list[tuple[datetime, Decimal]]:
    """產生 4 小時的合成資料：08:00 起冰機逐台啟動，10:30 三台同時加載造成尖峰。"""
    samples = []
    for minute in range(240):
        t = start + timedelta(minutes=minute)
        kw = D(420)                                   # IT 負載與基本空調
        if minute >= 30:
            kw += D(180)                              # 第 1 台冰機
        if minute >= 60:
            kw += D(170)                              # 第 2 台冰機
        if 150 <= minute < 175:
            kw += D(260)                              # 10:30 第 3 台冰機同時加載
        kw += D(minute % 7)                           # 小幅波動
        samples.append((t, kw))
    return samples


def demand_15min(samples):
    """依 00/15/30/45 分切齊的區間求平均功率；區間樣本不足 15 筆視為資料缺漏。"""
    buckets: dict[datetime, list[Decimal]] = {}
    for t, kw in samples:
        key = t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)
        buckets.setdefault(key, []).append(kw)
    result = {}
    for key, values in sorted(buckets.items()):
        if len(values) < 15:
            raise ValueError(f"{key:%H:%M} 區間只有 {len(values)} 筆，需先補值或標記缺漏")
        result[key] = (sum(values) / len(values)).quantize(D("0.1"), ROUND_HALF_UP)
    return result


def excess_charge(max_kw, contract_kw, unit_price, within_mult=D(2), beyond_mult=D(3)):
    excess = max(D(0), max_kw - contract_kw)
    tier1 = min(excess, (contract_kw * D("0.10")).quantize(D("0.1")))
    tier2 = excess - tier1
    charge = tier1 * unit_price * within_mult + tier2 * unit_price * beyond_mult
    return excess, tier1, tier2, charge.quantize(D("1"), ROUND_HALF_UP)


if __name__ == "__main__":
    samples = synthetic_samples(datetime(2026, 7, 15, 8, 0))
    demand = demand_15min(samples)
    peak_at, peak_kw = max(demand.items(), key=lambda kv: kv[1])
    print(f"15 分鐘區間數：{len(demand)}")
    print(f"最高需量：{peak_kw} kW（{peak_at:%H:%M}–{peak_at + timedelta(minutes=15):%H:%M}）")
    top3 = sorted(demand.items(), key=lambda kv: kv[1], reverse=True)[:3]
    print("前三高區間：" + "、".join(f"{t:%H:%M}={kw}" for t, kw in top3))

    contract_kw = D(900)
    unit_price = D("236.20")   # 假設的每 kW 月基本電費單價，僅供演算
    excess, t1, t2, charge = excess_charge(peak_kw, contract_kw, unit_price)
    print(f"契約容量 {contract_kw} kW，超約 {excess} kW（10% 內 {t1}、超過 10% {t2}）")
    print(f"假設單價下的超約加收：NT$ {charge:,}")

    # 錯開第 3 台冰機啟動（改為逐段加載，每 5 分鐘 +65 kW）的效果
    staged = []
    for t, kw in samples:
        m = int((t - samples[0][0]).total_seconds() // 60)
        if 150 <= m < 175:
            kw = kw - D(260) + D(65) * min(4, (m - 150) // 5 + 1)
        staged.append((t, kw))
    staged_peak = max(demand_15min(staged).values())
    print(f"分段加載後最高需量：{staged_peak} kW，"
          f"{'仍超約' if staged_peak > contract_kw else '未超約'}")
