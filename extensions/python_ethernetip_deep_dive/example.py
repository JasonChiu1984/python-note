"""組出與解析 EtherNet/IP 封裝標頭與 ListIdentity 回應（離線，標準函式庫 struct）。

封裝標頭固定 24 位元組，全部為 little-endian：
command(2) length(2) session_handle(4) status(4) sender_context(8) options(4)
"""
import struct

HEADER = struct.Struct("<HHII8sI")
LIST_IDENTITY = 0x0063


def build_list_identity(context=b"BMS-0001"):
    return HEADER.pack(LIST_IDENTITY, 0, 0, 0, context, 0)


def parse_header(data: bytes):
    if len(data) < HEADER.size:
        raise ValueError("封包不足 24 位元組")
    cmd, length, session, status, ctx, opts = HEADER.unpack_from(data)
    if len(data) != HEADER.size + length:
        raise ValueError(f"長度欄位 {length} 與實際資料 {len(data) - HEADER.size} 不符")
    return dict(command=hex(cmd), length=length, session=session, status=status, context=ctx)


def parse_identity_item(item: bytes):
    """CIP Identity 項目（Type 0x000C）。Socket Address 為 big-endian，其餘 little-endian。"""
    (version,) = struct.unpack_from("<H", item, 0)
    family, port, ip = struct.unpack_from(">hH4s", item, 2)
    vendor, dev_type, product, rev_major, rev_minor, status, serial, name_len = \
        struct.unpack_from("<HHHBBHIB", item, 18)
    name = item[33:33 + name_len].decode("ascii")
    state = item[33 + name_len]
    return dict(version=version, ip=".".join(map(str, ip)), port=port, vendor_id=vendor,
                device_type=dev_type, product_code=product, revision=f"{rev_major}.{rev_minor:03d}",
                serial=f"0x{serial:08X}", product_name=name, state=state)


def synthetic_response():
    name = b"1756-EN2T/D"
    item = (struct.pack("<H", 1) + struct.pack(">hH4s8s", 2, 44818, bytes([192, 168, 10, 20]), bytes(8))
            + struct.pack("<HHHBBHIB", 1, 12, 166, 11, 2, 0x0030, 0x00C0FFEE, len(name)) + name + bytes([3]))
    cpf = struct.pack("<HHH", 1, 0x000C, len(item)) + item          # item count, type, length
    return HEADER.pack(LIST_IDENTITY, len(cpf), 0, 0, b"BMS-0001", 0) + cpf


if __name__ == "__main__":
    req = build_list_identity()
    print("請求（UDP 44818 廣播）：", req.hex(" "))
    print("請求標頭：", parse_header(req))
    resp = synthetic_response()
    hdr = parse_header(resp)
    print("回應標頭：", hdr)
    count, item_type, item_len = struct.unpack_from("<HHH", resp, 24)
    print(f"CPF 項目數 {count}，型別 0x{item_type:04X}，長度 {item_len}")
    for k, v in parse_identity_item(resp[30:30 + item_len]).items():
        print(f"  {k:<13} {v}")
    try:
        parse_header(resp[:-3])
    except ValueError as e:
        print("截斷封包：", e)
