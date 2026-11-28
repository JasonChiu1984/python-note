"""RS-485 Modbus RTU 輪詢週期估算：字元時間、3.5 字元靜默、從站回應時間，找出排隊在哪裡（標準函式庫）。"""

BITS_PER_CHAR = 11          # 1 起始 + 8 資料 + 1 同位 + 1 停止（或 2 停止、無同位）


def char_time_ms(baud):
    return BITS_PER_CHAR / baud * 1000


def silent_ms(baud):
    """3.5 字元靜默；鮑率高於 19200 bps 時，Modbus 規範建議固定 1.75 ms。"""
    return 1.75 if baud > 19200 else 3.5 * char_time_ms(baud)


def transaction_ms(baud, regs, slave_resp_ms):
    req_bytes = 8                                  # 位址1＋功能碼1＋起始2＋數量2＋CRC2
    resp_bytes = 5 + 2 * regs                      # 位址1＋功能碼1＋位元組數1＋資料＋CRC2
    wire = (req_bytes + resp_bytes) * char_time_ms(baud)
    return wire + 2 * silent_ms(baud) + slave_resp_ms, wire


if __name__ == "__main__":
    slaves, regs, resp = 30, 20, 15.0
    for baud in (9600, 19200, 38400, 115200):
        tx, wire = transaction_ms(baud, regs, resp)
        cycle = slaves * tx / 1000
        print(f"{baud:>6} bps：單次交易 {tx:6.1f} ms（線上 {wire:5.1f} ms），{slaves} 台一輪 {cycle:5.2f} s")
    print()
    tx, _ = transaction_ms(19200, regs, resp)
    for clients in (1, 2, 4):
        print(f"{clients} 個上位系統共用同一閘道、各自每 2 s 輪詢一次：匯流排使用率 "
              f"{clients * slaves * tx / 2000:.0%}{'  ← 超過 100%，請求開始排隊' if clients * slaves * tx > 2000 else ''}")
    tx_timeout, _ = transaction_ms(19200, regs, 1000)
    print(f"若有 1 台從站離線、逾時設 1 s：每輪多 {tx_timeout - tx:.0f} ms，"
          f"一輪變成 {(slaves - 1) * tx / 1000 + tx_timeout / 1000:.2f} s")
