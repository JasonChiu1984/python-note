"""離線 SOAP 契約實驗；不啟動伺服器、不送 HTTP、不接真實設備。"""
import re
import unittest
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from email.message import Message

SOAP = {
    "1.1": "http://schemas.xmlsoap.org/soap/envelope/",
    "1.2": "http://www.w3.org/2003/05/soap-envelope",
}
MEDIA = {"1.1": "text/xml", "1.2": "application/soap+xml"}
NS = "urn:teaching:gateway:v1"
ACTION = NS + "/ReadPoint"
MAX_BYTES = 32768


def q(ns, name):
    return f"{{{ns}}}{name}"


class ContractError(ValueError):
    pass


class TransportError(RuntimeError):
    pass


class SoapFault(RuntimeError):
    def __init__(self, status, code_text, reason):
        # QName 字串只供本實驗顯示，不拿前綴作業務分類。
        super().__init__(f"HTTP {status}; {code_text}: {reason}")
        self.status, self.code_text, self.reason = status, code_text, reason


class BoundedTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.depth = self.nodes = 0

    def doctype(self, name, pubid, system):
        raise ContractError("此 SOAP profile 不接受 DTD")

    def start(self, tag, attrs):
        self.depth += 1
        self.nodes += 1
        if self.depth > 16 or self.nodes > 200 or len(attrs) > 12:
            raise ContractError("XML 結構超過實驗預算")
        return super().start(tag, attrs)

    def end(self, tag):
        self.depth -= 1
        return super().end(tag)


@dataclass(frozen=True)
class Reply:
    status: int
    content_type: str
    body: bytes


def headers(version):
    if version == "1.1":
        return {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{ACTION}"'}
    if version == "1.2":
        return {"Content-Type": f'application/soap+xml; charset=utf-8; action="{ACTION}"'}
    raise ContractError("未知 SOAP 版本")


def envelope(version, child):
    env = ET.Element(q(SOAP[version], "Envelope"))
    ET.SubElement(env, q(SOAP[version], "Body")).append(child)
    return ET.tostring(env, encoding="utf-8", xml_declaration=True)


def request(version, point):
    h = headers(version)
    if not re.fullmatch(r"[A-Z][A-Z0-9_-]{0,31}", point):
        raise ContractError("不符合本實驗的點位 ID")
    operation = ET.Element(q(NS, "ReadPoint"))
    ET.SubElement(operation, q(NS, "pointId")).text = point
    return h, envelope(version, operation)


def _type(raw):
    msg = Message()
    msg["Content-Type"] = raw
    return msg.get_content_type(), msg.get_param("charset")


def _parse(data):
    if not data or len(data) > MAX_BYTES:
        raise ContractError("訊息大小不在預算內")
    try:
        value = data.decode("utf-8", errors="strict")
        if "\0" in value:
            raise ContractError("XML 不接受 NUL")
        # 只接受明示 UTF-8 或省略 encoding 的 XML 宣告。
        if value.lstrip("\ufeff").startswith("<?xml "):
            declaration = value.split("?>", 1)[0]
            match = re.search(r"""\bencoding\s*=\s*(['"])([^'"]+)\1""", declaration)
            if match and match.group(2).lower() != "utf-8":
                raise ContractError("XML 宣告與實驗編碼不符")
        return ET.fromstring(value, parser=ET.XMLParser(target=BoundedTree()))
    except (UnicodeError, ET.ParseError) as exc:
        raise ContractError("不是有效的 UTF-8 XML") from exc


def read_response(version, reply):
    if version not in SOAP:
        raise ContractError("未知 SOAP 版本")
    media, charset = _type(reply.content_type)
    # Proxy 頁、無本文或其他非 SOAP 回應通常走傳輸錯誤。
    if media != MEDIA[version]:
        error = TransportError if not 200 <= reply.status < 300 else ContractError
        raise error(f"HTTP {reply.status} 非預期 Content-Type")
    if charset is not None and charset.lower() != "utf-8":
        raise ContractError("此實驗僅收 UTF-8")
    ns = SOAP[version]
    root = _parse(reply.body)
    if root.tag != q(ns, "Envelope"):
        raise ContractError("SOAP Envelope 版本不符")
    tags = [child.tag for child in root]
    # 本實驗不支援任何 SOAP Header / extension。不要略過 mustUnderstand。
    if tags != [q(ns, "Body")]:
        raise ContractError("只接受一個 Body，且本 profile 不接受 Header")
    body = root[0]
    if len(body) != 1:
        raise ContractError("本 profile 要求單一 Body 操作或 Fault")
    child = body[0]
    if child.tag == q(ns, "Fault"):
        if version == "1.1":
            code = child.findtext("faultcode")
            reason = child.findtext("faultstring")
        else:
            code = child.findtext(f"{q(ns, 'Code')}/{q(ns, 'Value')}")
            reason = child.findtext(f"{q(ns, 'Reason')}/{q(ns, 'Text')}")
        if not code or not reason:
            raise ContractError("Fault 缺少必要顯示欄位")
        raise SoapFault(reply.status, code, reason)
    if not 200 <= reply.status < 300:
        raise TransportError(f"HTTP {reply.status}; 無 SOAP Fault")
    if child.tag != q(NS, "ReadPointResponse") or [e.tag for e in child] != [q(NS, "value"), q(NS, "unit")]:
        raise ContractError("操作或欄位 QName 不符")
    # XSD 元素內容只允許子元素與 XML 定義的排版空白。
    inter_element = [child.text, *(element.tail for element in child)]
    if any((part or "").strip(" \t\r\n") for part in inter_element):
        raise ContractError("回應容器的元素間不得有文字")
    if any(len(e) or e.attrib for e in child):
        raise ContractError("欄位應為純文字")
    text = (child[0].text or "").strip()
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", text):
        raise ContractError("不是 xsd:decimal 的本實驗詞彙格式")
    value, unit = Decimal(text), child[1].text
    if unit != "degC" or not Decimal("-50") <= value <= Decimal("150"):
        raise ContractError("單位或量程不符合本實驗契約")
    return value


def success(version):
    child = ET.Element(q(NS, "ReadPointResponse"))
    ET.SubElement(child, q(NS, "value")).text = "7.25"
    ET.SubElement(child, q(NS, "unit")).text = "degC"
    return Reply(200, MEDIA[version], envelope(version, child))


def fault(version, status=None):
    env = SOAP[version]
    if version == "1.1":
        body = '<f:Fault><faultcode>f:Client</faultcode><faultstring>Unknown point</faultstring></f:Fault>'
    else:
        body = '<f:Fault><f:Code><f:Value>f:Sender</f:Value></f:Code><f:Reason><f:Text xml:lang="en">Unknown point</f:Text></f:Reason></f:Fault>'
    doc = f'<f:Envelope xmlns:f="{env}"><f:Body>{body}</f:Body></f:Envelope>'
    return Reply(status if status is not None else (500 if version == "1.1" else 400), MEDIA[version], doc.encode())


class Tests(unittest.TestCase):
    def test_success_decimal_both_versions(self):
        for version in SOAP:
            with self.subTest(version=version):
                self.assertEqual(read_response(version, success(version)), Decimal("7.25"))

    def test_response_wrapper_preserves_xml_formatting_whitespace(self):
        for version in SOAP:
            with self.subTest(version=version):
                node = ET.fromstring(success(version).body)[0][0]
                node.text = node[0].tail = node[1].tail = " \r\t\n "
                reply = Reply(200, MEDIA[version], envelope(version, node))
                self.assertEqual(read_response(version, reply), Decimal("7.25"))

    def test_response_wrapper_rejects_character_data(self):
        for version in SOAP:
            for slot in ("before_value", "between_fields", "after_unit"):
                for text in ("說明", "\u00a0"):
                    with self.subTest(version=version, slot=slot, text=text):
                        node = ET.fromstring(success(version).body)[0][0]
                        if slot == "before_value":
                            node.text = text
                        else:
                            node[int(slot == "after_unit")].tail = text
                        reply = Reply(200, MEDIA[version], envelope(version, node))
                        with self.assertRaisesRegex(ContractError, "元素間不得有文字"):
                            read_response(version, reply)

    def test_request_headers_and_ns(self):
        for v in SOAP:
            h, body = request(v, "CHW_01")
            self.assertEqual("SOAPAction" in h, v == "1.1")
            self.assertEqual("action=" in h["Content-Type"], v == "1.2")
            self.assertEqual(ET.fromstring(body)[0][0][0].tag, q(NS, "pointId"))

    def test_fault_before_http_classification(self):
        for v, status in (("1.1", 500), ("1.2", 400), ("1.2", 200)):
            with self.subTest(v=v, status=status), self.assertRaises(SoapFault) as err:
                read_response(v, fault(v, status))
            self.assertEqual(err.exception.status, status)

    def test_proxy_html(self):
        with self.assertRaises(TransportError):
            read_response("1.2", Reply(503, "text/html", b"proxy"))

    def test_wrong_envelope_even_if_media_type_correct(self):
        with self.assertRaises(ContractError):
            read_response("1.2", Reply(200, MEDIA["1.2"], success("1.1").body))

    def test_business_namespace_is_exact(self):
        item = success("1.2")
        with self.assertRaises(ContractError):
            read_response("1.2", Reply(200, item.content_type, item.body.replace(NS.encode(), b"urn:other")))

    def test_dtd_overbudget_or_non_utf8(self):
        for body in (b"<!DOCTYPE toy><toy/>", b"x" * (MAX_BYTES + 1), b"\xff", b"<a>" * 20 + b"</a>" * 20):
            with self.subTest(size=len(body)), self.assertRaises(ContractError):
                _parse(body)

    def test_unit_range_decimal_contract(self):
        item = success("1.2")
        for a, b in ((b"degC", b"degF"), (b"7.25", b"150.01"), (b"7.25", b"7e0")):
            with self.subTest(value=b), self.assertRaises(ContractError):
                read_response("1.2", Reply(200, item.content_type, item.body.replace(a, b)))

    def test_header_is_not_silently_ignored(self):
        env = SOAP["1.2"]
        body = f'<e:Envelope xmlns:e="{env}"><e:Header/><e:Body/></e:Envelope>'
        with self.assertRaises(ContractError):
            read_response("1.2", Reply(200, MEDIA["1.2"], body.encode()))


if __name__ == "__main__":
    unittest.main()
