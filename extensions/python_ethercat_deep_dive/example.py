"""EtherCAT 週期時間粗估與 WKC 期望值檢查（標準函式庫，參數皆為假設值）。

frame 依序經過每個 SubDevice 後折返。粗估：
週期下限 ≈ frame 序列化時間 + 每台 SubDevice 處理延遲 × 台數 × 2（去回）＋ 線路傳播延遲
"""
LINK_MBPS = 100
ESC_DELAY_US = 0.6            # 假設每台 ESC 轉送延遲（依晶片與連接埠而異）
CABLE_NS_PER_M = 5.0          # 銅纜約 5 ns/m


MAX_ECAT_PAYLOAD = 1498       # 乙太網路 payload 1500 − EtherCAT 標頭 2


def frames_for(pdo_bytes):
    """每個 datagram 有 10 B 標頭＋2 B WKC；超過單一 frame 容量時拆成多個 frame。"""
    per_frame = MAX_ECAT_PAYLOAD - 12
    sizes = []
    while pdo_bytes > 0:
        chunk = min(pdo_bytes, per_frame)
        sizes.append(max(64, 14 + 2 + 12 + chunk + 4))      # 以太網標頭＋EtherCAT 標頭＋datagram＋FCS
        pdo_bytes -= chunk
    return sizes


def cycle_estimate(devices, pdo_bytes, cable_m):
    sizes = frames_for(pdo_bytes)
    ser = sum((s + 20) * 8 / LINK_MBPS for s in sizes)        # 另加前導碼與幀間隙 20 B
    prop = devices * ESC_DELAY_US * 2 + cable_m * CABLE_NS_PER_M * 2 / 1000
    return ser + prop, sizes


def expected_wkc(n_read, n_write, n_readwrite):
    """依預期映射加總 LRW 貢獻；不適用於獨立讀取或寫入命令。"""
    return (n_read * lrw_contribution(True, False)
            + n_write * lrw_contribution(False, True)
            + n_readwrite * lrw_contribution(True, True))


def lrw_contribution(read_ok: bool, write_ok: bool) -> int:
    """LRW 中讀成功 +1、寫成功 +2；兩者分開計算。"""
    return int(read_ok) + 2 * int(write_ok)


def compare_wkc(expected: int, received: int) -> str:
    if received == expected:
        return "WKC 相符；仍須另驗資料品質"
    return "WKC 不符；當筆資料不可用，不能只靠總數定位"


if __name__ == "__main__":
    for devices, per_dev in ((10, 8), (50, 8), (100, 16)):
        pdo = devices * per_dev
        us, sizes = cycle_estimate(devices, pdo, cable_m=devices * 3)
        print(f"{devices:>3} 台 × {per_dev:>2} B PDO：{len(sizes)} 個 frame {sizes} B，週期下限約 {us:6.1f} µs")
    exp = expected_wkc(n_read=4, n_write=2, n_readwrite=6)
    print(f"\n4 台只讀、2 台只寫、6 台讀寫的 LRW：期望 WKC = {exp}")
    rw = lrw_contribution(True, True)
    cases = [
        ("符合期望", exp),
        ("只讀站未完成讀取", exp - lrw_contribution(True, False)),
        ("讀寫站讀失敗、寫成功", exp - rw + lrw_contribution(False, True)),
        ("讀寫站讀成功、寫失敗", exp - rw + lrw_contribution(True, False)),
        ("讀寫站讀寫皆失敗", exp - rw),
    ]
    for label, got in cases:
        print(f"  {label} → WKC {got}：{compare_wkc(exp, got)}")
