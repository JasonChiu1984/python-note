"""組出 SOAP 1.1 與 1.2 請求、辨識版本，並解析回應與 Fault（標準函式庫 xml.etree）。"""
import math
import xml.etree.ElementTree as ET

SOAP11 = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP12 = "http://www.w3.org/2003/05/soap-envelope"
APP = "urn:example:bms"


def envelope(version, body_xml):
    ns = SOAP11 if version == "1.1" else SOAP12
    return f'<soap:Envelope xmlns:soap="{ns}"><soap:Body>{body_xml}</soap:Body></soap:Envelope>'


def headers(version, action):
    if version == "1.1":
        return {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{action}"'}
    return {"Content-Type": f'application/soap+xml; charset=utf-8; action="{action}"'}


def detect(xml_text):
    tag = ET.fromstring(xml_text).tag
    return {f"{{{SOAP11}}}Envelope": "SOAP 1.1", f"{{{SOAP12}}}Envelope": "SOAP 1.2"}.get(tag, "不是 SOAP Envelope")


def parse_response(xml_text: str):
    """只解析本教材的單一回應或 Fault；不是通用 SOAP 或 XML 安全驗證器。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "錯誤", None, "XML 無法剖析"
    ns = next((n for n in (SOAP11, SOAP12) if root.tag == f"{{{n}}}Envelope"), None)
    if ns is None:
        return "錯誤", None, "不是 SOAP Envelope"
    bodies = root.findall(f"{{{ns}}}Body")
    if len(bodies) != 1 or len(bodies[0]) != 1:
        return "錯誤", None, "本算例要求唯一 Body 與單一內容元素"
    item = bodies[0][0]
    if item.tag == f"{{{ns}}}Fault":
        paths = ("faultcode", "faultstring") if ns == SOAP11 else (
            f"{{{ns}}}Code/{{{ns}}}Value", f"{{{ns}}}Reason/{{{ns}}}Text"
        )
        code, reason = (item.findtext(path, "").strip() for path in paths)
        return ("Fault", code, reason) if code and reason else ("錯誤", None, "Fault 缺少代碼或原因")
    if item.tag != f"{{{APP}}}GetPointResponse":
        return "錯誤", None, "不是預期的業務回應"
    values = item.findall(f"{{{APP}}}value")
    if len(values) != 1 or values[0].text is None or len(values[0]):
        return "錯誤", None, "需要一個純文字 value"
    v = values[0]
    try:
        reading = float(v.text)
    except ValueError:
        return "錯誤", None, "讀值不是數字"
    if not math.isfinite(reading):
        return "錯誤", None, "讀值必須有限"
    return "OK", reading, v.get("unit")


if __name__ == "__main__":
    req = f'<b:GetPoint xmlns:b="{APP}"><b:name>AHU1_SAT</b:name></b:GetPoint>'
    for ver in ("1.1", "1.2"):
        env = envelope(ver, req)
        print(f"SOAP {ver} 標頭：{headers(ver, APP + '#GetPoint')}")
        print(f"  辨識：{detect(env)}")
    ok = envelope("1.1", f'<b:GetPointResponse xmlns:b="{APP}"><b:value unit="degC">22.5</b:value></b:GetPointResponse>')
    print("回應：", parse_response(ok))
    fault11 = envelope("1.1", "<soap:Fault><faultcode>soap:Client</faultcode><faultstring>Unknown point</faultstring></soap:Fault>")
    print("1.1 Fault：", parse_response(fault11))
    fault12 = envelope("1.2", f'<soap:Fault><soap:Code><soap:Value>soap:Sender</soap:Value></soap:Code>'
                       f'<soap:Reason><soap:Text xml:lang="en">Unknown point</soap:Text></soap:Reason></soap:Fault>')
    print("1.2 Fault：", parse_response(fault12))
