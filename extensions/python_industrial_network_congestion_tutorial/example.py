"""RS-485 Modbus RTU 輪詢週期估算：字元時間、3.5 字元靜默、從站回應時間，找出排隊在哪裡（標準函式庫）。"""

READ_REQUEST_BYTES = 8       # 位址1＋功能碼1＋起始2＋數量2＋CRC2
BITS_PER_CHAR = 11          # 1 起始 + 8 資料 + 1 同位 + 1 停止（或 2 停止、無同位）


def char_time_ms(baud):
    return BITS_PER_CHAR / baud * 1000


def silent_ms(baud):
    """3.5 字元靜默；Modbus 規範在高於 19200 bps 時建議固定 1.75 ms。"""
    return 1.75 if baud > 19200 else 3.5 * char_time_ms(baud)


def transaction_ms(baud, regs, slave_resp_ms):
    resp_bytes = 5 + 2 * regs                      # 位址1＋功能碼1＋位元組數1＋資料＋CRC2
    wire = (READ_REQUEST_BYTES + resp_bytes) * char_time_ms(baud)
    return wire + 2 * silent_ms(baud) + slave_resp_ms, wire


def no_reply_ms(baud, timeout_ms, guard_ms=0):
    """逾時從請求送完後開始計；無回應框，預設不重試或額外等待。"""
    if timeout_ms < 0 or guard_ms < 0:
        raise ValueError("等待時間不得為負")
    request_wire = READ_REQUEST_BYTES * char_time_ms(baud)
    return request_wire + timeout_ms + guard_ms, request_wire


if __name__ == "__main__":
    slaves, regs, resp = 30, 20, 15.0
    for baud in (9600, 19200, 38400, 115200):
        tx, wire = transaction_ms(baud, regs, resp)
        cycle = slaves * tx / 1000
        print(f"{baud:>6} bps：單次交易 {tx:6.1f} ms（線上 {wire:5.1f} ms），{slaves} 台一輪 {cycle:5.2f} s")
    print()
    tx, _ = transaction_ms(19200, regs, resp)
    for clients in (1, 2, 4):
        print(f"{clients} 個上位系統共用同一閘道、各自每 2 s 輪詢一次：輪詢所需服務時間 ÷ 可用時間 "
              f"{clients * slaves * tx / 2000:.0%}{'  ← 需求超過產能，可能排隊或被拒絕' if clients * slaves * tx > 2000 else ''}")
    for timeout in (1000, 100):
        slot, wire = no_reply_ms(19200, timeout)
        cycle = ((slaves - 1) * tx + slot) / 1000
        print(f"1 台不回覆、逾時 {timeout} ms：離線槽 {slot:.3f} ms"
              f"（實際請求傳輸 {wire:.3f} ms），一輪 {cycle:.3f} s")
