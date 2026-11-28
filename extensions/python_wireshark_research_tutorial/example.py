"""不用 Wireshark 也能讀 pcap：產生一個含 Modbus TCP 請求的 pcap，再逐層解析（標準函式庫 struct）。"""
import struct


def build_pcap():
    mbap_pdu = struct.pack(">HHHB", 0x002A, 0, 6, 1) + struct.pack(">BHH", 3, 0, 10)   # FC03 讀 10 個暫存器
    tcp = struct.pack(">HHIIBBHHH", 50123, 502, 1000, 2000, 5 << 4, 0x18, 8192, 0, 0)
    ip_total = 20 + len(tcp) + len(mbap_pdu)
    ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, ip_total, 1, 0x4000, 64, 6, 0,
                     bytes([192, 168, 10, 5]), bytes([192, 168, 10, 20]))
    eth = bytes.fromhex("001122334455") + bytes.fromhex("66778899aabb") + struct.pack(">H", 0x0800)
    frame = eth + ip + tcp + mbap_pdu
    global_hdr = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)          # LINKTYPE_ETHERNET
    rec = struct.pack("<IIII", 1_795_800_000, 123_456, len(frame), len(frame))
    return global_hdr + rec + frame


def parse(data):
    magic, vmaj, vmin, _, _, snaplen, linktype = struct.unpack_from("<IHHiIII", data, 0)
    assert magic == 0xA1B2C3D4, "非 little-endian 微秒格式 pcap"
    print(f"pcap v{vmaj}.{vmin}，snaplen {snaplen}，linktype {linktype}（1 = Ethernet）")
    off = 24
    while off < len(data):
        sec, usec, incl, orig = struct.unpack_from("<IIII", data, off)
        frame = data[off + 16: off + 16 + incl]
        off += 16 + incl
        dst, src, etype = frame[:6], frame[6:12], struct.unpack_from(">H", frame, 12)[0]
        print(f"時間 {sec}.{usec:06d}，長度 {incl}/{orig}，EtherType 0x{etype:04X}")
        ihl = (frame[14] & 0x0F) * 4
        proto = frame[14 + 9]
        sip, dip = frame[14 + 12:14 + 16], frame[14 + 16:14 + 20]
        print(f"IPv4 {'.'.join(map(str, sip))} → {'.'.join(map(str, dip))}，協定 {proto}（6 = TCP），IHL {ihl}")
        t = 14 + ihl
        sport, dport, seq, ack, doff = struct.unpack_from(">HHIIB", frame, t)
        hlen = (doff >> 4) * 4
        print(f"TCP {sport} → {dport}，seq {seq}，標頭 {hlen} bytes")
        m = t + hlen
        tid, pid, length, uid, fc, start, qty = struct.unpack_from(">HHHBBHH", frame, m)
        print(f"Modbus TCP：交易 {tid}，協定 {pid}，長度 {length}，Unit {uid}，FC{fc:02d} 起始 {start} 數量 {qty}")


if __name__ == "__main__":
    data = build_pcap()
    print(f"pcap 共 {len(data)} bytes")
    parse(data)
    print("等效 Wireshark 顯示篩選：", "modbus.func_code == 3 && ip.dst == 192.168.10.20")
