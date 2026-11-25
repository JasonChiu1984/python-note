"""只產生、讀取合成 PCAP；不抓包、不傳送、不執行資料內容。"""
import argparse
import json
from pathlib import Path
from struct import pack, unpack_from
import unittest

MAGIC = {
    bytes.fromhex("d4c3b2a1"): ("<", 10**6),
    bytes.fromhex("a1b2c3d4"): (">", 10**6),
    bytes.fromhex("4d3cb2a1"): ("<", 10**9),
    bytes.fromhex("a1b23c4d"): (">", 10**9),
}
FRAME = bytes.fromhex(
    "0200000000020200000000010800"
    "450000200001000040118e95c0000201c6336402"
    "30391f90000c0000 4c414221"
) + bytes(14)
TAGGED = FRAME[:12] + bytes.fromhex("81000064") + FRAME[12:]


def fixture(endian="<", precision=10**6, linkword=1):
    magic = next(k for k, v in MAGIC.items() if v == (endian, precision))
    out = magic + pack(endian + "HHIIII", 2, 4, 0, 0, 64, linkword)
    for n, data in enumerate((FRAME, TAGGED, TAGGED[:-34]), start=1):
        original = len(TAGGED) if n > 1 else len(FRAME)
        out += pack(endian + "IIII", 1_700_000_000 + n, precision // 4, len(data), original) + data
    return out


def decode_frame(data):
    if len(data) < 14:
        return {"status": "truncated_ethernet"}
    etype = unpack_from("!H", data, 12)[0]
    pos = 14
    vlan = None
    if etype == 0x8100:
        if len(data) < 18:
            return {"status": "truncated_vlan"}
        tag, etype = unpack_from("!HH", data, 14)
        vlan = tag & 0x0FFF
        pos = 18
    layer = {"ethertype": f"0x{etype:04x}", "vlan": vlan, "l3_offset": pos}
    if etype != 0x0800:
        return {**layer, "status": "unsupported_ethertype"}
    if len(data) - pos < 20:
        return {**layer, "status": "truncated_ipv4_header"}
    vihl = data[pos]
    ihl = (vihl & 15) * 4
    total = unpack_from("!H", data, pos + 2)[0]
    if (vihl >> 4) != 4 or ihl < 20 or total < ihl:
        return {**layer, "status": "invalid_ipv4_length"}
    if total > len(data) - pos:
        return {**layer, "status": "truncated_ipv4_datagram"}
    if unpack_from("!H", data, pos + 6)[0] & 0x3FFF:
        return {**layer, "status": "ipv4_fragment_not_reassembled"}
    proto = data[pos + 9]
    layer.update(ipv4_bytes=total, ipv4_header_bytes=ihl, protocol=proto)
    if proto != 17:
        return {**layer, "status": "unsupported_l4"}
    if total - ihl < 8:
        return {**layer, "status": "truncated_udp_header"}
    src, dst, size, checksum = unpack_from("!HHHH", data, pos + ihl)
    if not 8 <= size <= total - ihl:
        return {**layer, "status": "invalid_udp_length"}
    return {**layer, "status": "udp", "source_port": src, "destination_port": dst,
            "udp_length": size, "udp_checksum_field": checksum,
            "payload_length": size-8, "ethernet_tail_bytes": len(data)-pos-total}


def inspect(data):
    if len(data) < 24:
        raise ValueError("全域標頭不足 24 bytes")
    magic = data[:4]
    if magic not in MAGIC:
        raise ValueError("非本例支援的 classic PCAP magic（不讀 PCAPNG）")
    endian, precision = MAGIC[magic]
    major, minor, _, _, snaplen, linkword = unpack_from(endian + "HHIIII", data, 4)
    if (major, minor) != (2, 4) or snaplen <= 0:
        raise ValueError("未知 PCAP 版本或無效 snaplen")
    linktype = linkword & 0xFFFF
    if linktype != 1 or linkword != 1:
        raise ValueError(f"不支援鏈路型別或附加旗標：{linktype}／0x{linkword:08x}")
    records = []
    pos = 24
    while pos < len(data):
        if len(data) - pos < 16:
            raise ValueError("封包紀錄標頭截斷")
        sec, frac, captured, original = unpack_from(endian + "IIII", data, pos)
        pos += 16
        if frac >= precision or captured > snaplen or captured > original:
            raise ValueError("時間子秒、捕獲長度、原始長度或 snaplen 矛盾")
        if captured > len(data) - pos:
            raise ValueError("檔案內容缺少 caplen 宣告的位元組")
        payload = data[pos:pos+captured]
        pos += captured
        records.append({
            "record": len(records)+1, "seconds_since_epoch": sec, "fraction": frac,
            "captured_bytes": captured, "original_bytes": original,
            "capture_truncated": captured < original, **decode_frame(payload),
        })
    return {"endian": "little" if endian == "<" else "big",
            "timestamp_unit": "us" if precision == 10**6 else "ns",
            "snaplen": snaplen, "linktype": linktype, "records": records}


class TestLab(unittest.TestCase):
    def test_record_evidence(self):
        report = inspect(fixture())
        a,b,c = report["records"]
        self.assertEqual((report["snaplen"], report["linktype"]), (64,1))
        self.assertEqual((a["captured_bytes"], a["l3_offset"], a["udp_length"], a["ethernet_tail_bytes"]), (60,14,12,14))
        self.assertEqual((b["captured_bytes"], b["vlan"], b["l3_offset"], b["payload_length"]), (64,100,18,4))
        self.assertTrue(c["capture_truncated"])
        self.assertEqual((c["captured_bytes"],c["original_bytes"],c["status"]), (30,64,"truncated_ipv4_header"))

    def test_magic_matrix(self):
        for endian, fraction in MAGIC.values():
            r = inspect(fixture(endian, fraction))
            self.assertEqual(r["records"][0]["fraction"], fraction//4)

    def test_unknown_link_and_container(self):
        with self.assertRaisesRegex(ValueError, "鏈路"):
            inspect(fixture(linkword=101))
        with self.assertRaisesRegex(ValueError, "magic"):
            inspect(bytes(24))

    def test_truncated_file_not_snaplen(self):
        with self.assertRaisesRegex(ValueError, "caplen"):
            inspect(fixture()[:-1])

    def test_unknown_ethertype(self):
        self.assertEqual(decode_frame(FRAME[:12]+bytes.fromhex("86dd")+FRAME[14:])["status"], "unsupported_ethertype")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--write", type=Path, metavar="PCAP", help="建立合成檔；不覆寫")
    mode.add_argument("--read", type=Path, metavar="PCAP", help="讀取本機合成檔")
    args = p.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestLab))
        return 0 if result.wasSuccessful() else 1
    try:
        data=fixture()
        if args.write:
            with args.write.open("xb") as out:
                out.write(data)
        if args.read:
            with args.read.open("rb") as src:
                data=src.read(1_048_577)
            if len(data) > 1_048_576:
                raise ValueError("本實驗讀檔上限 1 MiB")
        print(json.dumps(inspect(data), indent=2, ensure_ascii=False))
    except (OSError, ValueError) as e:
        p.exit(2, f"停止解析：{e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
