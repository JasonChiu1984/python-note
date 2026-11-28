"""MQTT 主題過濾、Remaining Length 編碼與 QoS 1 重複投遞的冪等落地（標準函式庫模擬）。"""


def topic_matches(topic_filter: str, topic: str) -> bool:
    """依 MQTT 規則比對：+ 比對單一層級，# 只能在最後、比對其後所有層級。"""
    f_parts, t_parts = topic_filter.split("/"), topic.split("/")
    if topic.startswith("$") and topic_filter[:1] in ("+", "#"):
        return False                      # $SYS 等系統主題不被開頭的萬用字元匹配
    for i, part in enumerate(f_parts):
        if part == "#":
            if i != len(f_parts) - 1:
                raise ValueError("# 只能出現在過濾字串最後一層")
            return True
        if i >= len(t_parts):
            return False
        if part != "+" and part != t_parts[i]:
            return False
    return len(f_parts) == len(t_parts)


def encode_remaining_length(n: int) -> bytes:
    """MQTT 可變長度整數：每位元組 7 bits，最高位表示後面還有位元組，最多 4 位元組。"""
    if not 0 <= n <= 268_435_455:
        raise ValueError("超出 MQTT 允許範圍")
    out = bytearray()
    while True:
        byte, n = n % 128, n // 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


class IdempotentSink:
    """QoS 1 是「至少一次」：同一則訊息可能重送，落地端以 (裝置, 序號) 去重。"""

    def __init__(self):
        self.seen: set[tuple[str, int]] = set()
        self.rows: list[tuple[str, int, float]] = []

    def handle(self, device: str, seq: int, value: float) -> str:
        key = (device, seq)
        if key in self.seen:
            return "重複，略過"
        self.seen.add(key)
        self.rows.append((device, seq, value))
        return "寫入"


if __name__ == "__main__":
    cases = [
        ("site/+/ahu/+/sat", "site/b1/ahu/01/sat"),
        ("site/+/ahu/+/sat", "site/b1/ahu/01/rat"),
        ("site/b1/#", "site/b1/chiller/02/kw"),
        ("site/b1/#", "site/b1"),
        ("+/b1/ahu/01/sat", "site/b1/ahu/01/sat"),
        ("#", "$SYS/broker/uptime"),
    ]
    for f, t in cases:
        print(f"{f:<18} vs {t:<24} -> {topic_matches(f, t)}")

    for n in (0, 127, 128, 16_383, 16_384, 2_097_152):
        print(f"Remaining Length {n:>9,} -> {encode_remaining_length(n).hex(' ')}")

    sink = IdempotentSink()
    # 斷線重連後 broker 重送了序號 1002（DUP 旗標），且到達順序與送出順序不同
    deliveries = [("AHU-01", 1001, 13.2), ("AHU-01", 1002, 13.4), ("AHU-01", 1002, 13.4),
                  ("AHU-01", 1004, 13.9), ("AHU-01", 1003, 13.6)]
    for d in deliveries:
        print(f"收到 {d} -> {sink.handle(*d)}")
    seqs = sorted(r[1] for r in sink.rows)
    gaps = [s for s in range(seqs[0], seqs[-1] + 1) if s not in seqs]
    print(f"落地 {len(sink.rows)} 筆，序號缺口：{gaps or '無'}")
