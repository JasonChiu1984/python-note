"""手動以 BER 編碼 SNMPv2c GetRequest，並示範 Counter32 回捲時的速率計算（標準函式庫）。

SNMPv1/v2c 的 community 以明文傳送，只適合隔離的管理網段；需要認證與加密時用 SNMPv3（authPriv）。
"""


def tlv(tag, value: bytes):
    n = len(value)
    length = bytes([n]) if n < 128 else bytes([0x80 | ((n.bit_length() + 7) // 8)]) + n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([tag]) + length + value


def integer(v):
    return tlv(0x02, v.to_bytes(max(1, (v.bit_length() + 8) // 8), "big", signed=True))


def oid(dotted):
    parts = [int(x) for x in dotted.split(".")]
    body = bytes([40 * parts[0] + parts[1]])
    for p in parts[2:]:
        chunk = [p & 0x7F]
        p >>= 7
        while p:
            chunk.insert(0, 0x80 | (p & 0x7F))
            p >>= 7
        body += bytes(chunk)
    return tlv(0x06, body)


def get_request(community, request_id, oids):
    varbinds = tlv(0x30, b"".join(tlv(0x30, oid(o) + tlv(0x05, b"")) for o in oids))
    pdu = tlv(0xA0, integer(request_id) + integer(0) + integer(0) + varbinds)
    return tlv(0x30, integer(1) + tlv(0x04, community.encode()) + pdu)      # version 1 = v2c


def rate(prev, curr, seconds, bits=32):
    delta = curr - prev if curr >= prev else curr + 2 ** bits - prev
    return delta / seconds


if __name__ == "__main__":
    pkt = get_request("public", 0x1234, ["1.3.6.1.2.1.1.3.0", "1.3.6.1.2.1.2.2.1.10.1"])
    print(f"GetRequest {len(pkt)} bytes：", pkt.hex(" "))
    print("sysUpTime.0 OID 編碼：", oid("1.3.6.1.2.1.1.3.0").hex(" "))
    print("community 'public' 以明文出現在封包中：", b"public" in pkt)
    prev, curr = 4_294_000_000, 1_500_000            # ifInOctets 在兩次輪詢間回捲
    bps = rate(prev, curr, 60) * 8
    print(f"Counter32 回捲：{prev:,} → {curr:,}，60 秒平均 {bps / 1e6:.2f} Mbps")
    print(f"同樣流量若用 1 Gbps 滿載，Counter32 約 {2 ** 32 * 8 / 1e9:.0f} 秒就回捲一次；高速介面請改讀 ifHCInOctets（Counter64）")
