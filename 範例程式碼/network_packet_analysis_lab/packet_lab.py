"""Decode only the two built-in documentation fixtures. No file or network input."""

import argparse
import ipaddress
import json
import struct

FIXTURES = {
    "udp": bytes.fromhex(
        "0200000000020200000000010800 "
        "450000200001000040118e95c0000201c6336402 "
        "30391f90000c0000 4c414221 "
        "0000000000000000000000000000"  # Ethernet padding, not part of IPv4
    ),
    "tcp": bytes.fromhex(
        "0200000000020200000000010800 "
        "460000330002400040064c8bc0000201c6336402 01010000 "
        "303901bb000000010000000260184000b2540000 01010000 "
        "4c4142"
    ),
}


class ParseError(ValueError):
    """Record is incomplete, inconsistent, or intentionally unsupported."""


def bounded(view: memoryview, start: int, length: int, name: str) -> memoryview:
    if start < 0 or length < 0 or start + length > len(view):
        raise ParseError(f"{name}: truncated")
    return view[start:start + length]


def mac(view: memoryview) -> str:
    return view.hex(":")


def parse_frame(frame: bytes) -> dict:
    captured = memoryview(frame)
    eth = bounded(captured, 0, 14, "Ethernet II")
    ether_type, = struct.unpack_from("!H", eth, 12)
    if ether_type != 0x0800:
        raise ParseError("EtherType: only untagged IPv4 (0x0800) is supported")

    fixed_ip = bounded(captured, 14, 20, "IPv4 minimum header")
    version, ihl = fixed_ip[0] >> 4, (fixed_ip[0] & 0xF) * 4
    if version != 4 or ihl < 20:
        raise ParseError("IPv4: invalid version or IHL")
    total, identification, frag = struct.unpack_from("!HHH", fixed_ip, 2)
    if total < ihl:
        raise ParseError("IPv4: Total Length is smaller than header")
    ip = bounded(captured, 14, total, "IPv4 Total Length")
    if frag & 0x8000:
        raise ParseError("IPv4: reserved fragmentation flag is set")
    if frag & 0x3FFF:  # MF (0x2000) or non-zero offset, not DF (0x4000)
        raise ParseError("IPv4: fragmented datagrams are unsupported")

    protocol = fixed_ip[9]
    segment = ip[ihl:]
    if protocol == 17:
        header = bounded(segment, 0, 8, "UDP minimum header")
        src_port, dst_port, length, checksum = struct.unpack_from("!HHHH", header)
        if length < 8 or length != len(segment):
            raise ParseError("UDP: length differs from IPv4 payload")
        payload = segment[8:length]
        info = {"kind": "UDP", "header_bytes": 8, "length": length,
                "checksum_field": checksum}
    elif protocol == 6:
        header = bounded(segment, 0, 20, "TCP minimum header")
        src_port, dst_port, seq, ack = struct.unpack_from("!HHII", header)
        offset = (header[12] >> 4) * 4
        if offset < 20:
            raise ParseError("TCP: invalid Data Offset")
        bounded(segment, 0, offset, "TCP header including options")
        payload = segment[offset:]
        checksum, = struct.unpack_from("!H", header, 16)
        info = {"kind": "TCP", "header_bytes": offset, "sequence": seq,
                "acknowledgment": ack, "flags_low8_hex": f"{header[13]:02x}",
                "checksum_field": checksum}
    else:
        raise ParseError("IPv4 Protocol: only TCP (6) and UDP (17) are supported")

    return {
        "captured_bytes": len(captured),
        "ethernet": {"source": mac(eth[6:12]), "destination": mac(eth[:6]),
                     "ethertype_hex": f"{ether_type:04x}"},
        "ipv4": {"source": str(ipaddress.IPv4Address(bytes(fixed_ip[12:16]))),
                 "destination": str(ipaddress.IPv4Address(bytes(fixed_ip[16:20]))),
                 "header_bytes": ihl, "total_length": total, "ttl": fixed_ip[8],
                 "identification": identification, "protocol": protocol,
                 "dont_fragment": bool(frag & 0x4000)},
        "transport": {**info, "source_port": src_port, "destination_port": dst_port},
        "payload_length": len(payload), "payload_hex": payload.hex(),
        "unparsed_ethernet_tail_bytes": len(captured) - 14 - total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", choices=FIXTURES)
    args = parser.parse_args()
    try:
        result = parse_frame(FIXTURES[args.fixture])
    except ParseError as exc:
        parser.exit(1, f"parse error: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
