"""組出 SOAP 1.1 與 1.2 請求、辨識版本，並解析回應與 Fault（標準函式庫 xml.etree）。"""
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


def parse_response(xml_text):
    """回傳（狀態, 代碼, 訊息或值）；任何輸入都只回傳判定結果，不讓例外外洩。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "錯誤", None, "XML 無法剖析"
    ns = root.tag[1:].split("}")[0] if root.tag.startswith("{") else ""
    if ns not in (SOAP11, SOAP12) or root.tag != f"{{{ns}}}Envelope":
        return "錯誤", None, "不是 SOAP Envelope"
    body = root.find(f"{{{ns}}}Body")
    if body is None:
        return "錯誤", None, "缺少 Body"
    fault = body.find(f"{{{ns}}}Fault")
    if fault is not None:
        if ns == SOAP11:
            return "Fault", fault.findtext("faultcode"), fault.findtext("faultstring")
        return ("Fault", fault.findtext(f"{{{ns}}}Code/{{{ns}}}Value"),
                fault.findtext(f"{{{ns}}}Reason/{{{ns}}}Text"))
    v = body.find(f"{{{APP}}}GetPointResponse/{{{APP}}}value")
    if v is None or v.text is None:
        return "錯誤", None, "回應缺少 value"
    return "OK", float(v.text), v.get("unit")


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
    print("無命名空間：", parse_response("<Envelope><Body/></Envelope>"))
    print("缺少 Body：", parse_response(f'<soap:Envelope xmlns:soap="{SOAP11}"/>'))
