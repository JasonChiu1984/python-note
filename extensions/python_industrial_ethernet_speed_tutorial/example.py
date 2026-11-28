"""Modbus TCP 輪詢時間預算：100 Mbps 與 1 Gbps 的差異在哪裡（標準函式庫）。

一次交易 = 請求在線上的序列化時間 + 交換器轉送 + 設備處理時間 + 回應序列化時間。
乙太網路每幀還有前導碼／SFD 8 bytes 與幀間隙 12 bytes，最小幀 64 bytes（含 FCS）。
"""
ETH_OVERHEAD = 14 + 4            # MAC 標頭＋FCS
WIRE_EXTRA = 8 + 12              # 前導碼/SFD＋幀間隙
IP_TCP = 20 + 20
MBAP = 7


def frame_bytes(pdu_len):
    payload = IP_TCP + MBAP + pdu_len
    frame = max(64, payload + ETH_OVERHEAD)
    return frame, frame + WIRE_EXTRA


def serialization_us(wire_bytes, mbps):
    return wire_bytes * 8 / mbps


if __name__ == "__main__":
    req_pdu = 5                                  # FC03：功能碼 1＋起始位址 2＋數量 2
    for regs in (10, 125):
        resp_pdu = 2 + regs * 2                  # 功能碼＋位元組數＋資料
        rq, rq_wire = frame_bytes(req_pdu)
        rs, rs_wire = frame_bytes(resp_pdu)
        print(f"讀 {regs} 個暫存器：請求幀 {rq} B，回應幀 {rs} B（線上另加 20 B）")
        for mbps in (100, 1000):
            wire = serialization_us(rq_wire, mbps) + serialization_us(rs_wire, mbps)
            switch = 2 * 2 * 5.0 if mbps == 100 else 2 * 2 * 1.0   # 兩台交換器、來回，假設轉送延遲
            device = 4000.0                       # 假設設備回應 4 ms
            total = wire + switch + device
            print(f"  {mbps:>4} Mbps：線上 {wire:6.2f} µs＋交換器 {switch:4.1f} µs＋設備 {device:.0f} µs"
                  f" = {total / 1000:.3f} ms（線上時間占 {wire / total:.2%}）")
    devices, per_tx_ms = 60, 4.03
    print(f"\n{devices} 台電表依序輪詢、每台一次交易約 {per_tx_ms} ms：一輪 {devices * per_tx_ms / 1000:.2f} s")
    print("升級 1 Gbps 幾乎不改變這個數字；要縮短輪詢週期，應合併讀取範圍、平行連線或減少點數。")
