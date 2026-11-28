"""不需 openpyxl 也能讀 .xlsx：xlsx 是 zip 包著 XML。產生一個最小活頁簿再讀回，並區分數值、字串與公式（標準函式庫）。

正式處理請用 openpyxl（本範例只是讓你理解檔案結構，以及「公式儲存格沒有快取值」的意義）。
"""
import io
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

SHEET = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>點位</t></is></c><c r="B1" t="inlineStr"><is><t>位址</t></is></c><c r="C1" t="inlineStr"><is><t>讀值</t></is></c><c r="D1" t="inlineStr"><is><t>超溫</t></is></c></row>
<row r="2"><c r="A2" t="inlineStr"><is><t>AHU1_SAT</t></is></c><c r="B2" t="inlineStr"><is><t>001</t></is></c><c r="C2"><v>22.5</v></c><c r="D2"><f>C2&gt;24</f><v>0</v></c></row>
<row r="3"><c r="A3" t="inlineStr"><is><t>AHU2_SAT</t></is></c><c r="B3" t="inlineStr"><is><t>002</t></is></c><c r="C3"><v>25.2</v></c><c r="D3"><f>C3&gt;24</f></c></row>
</sheetData></worksheet>"""


def make_xlsx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", SHEET)
    return buf.getvalue()


def read_cells(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    for c in root.iterfind(".//m:c", NS):
        ref, typ = c.get("r"), c.get("t")
        f, v = c.find("m:f", NS), c.find("m:v", NS)
        if typ == "inlineStr":
            yield ref, "字串", c.find(".//m:t", NS).text
        elif f is not None:
            yield ref, "公式", f"={f.text}，快取值 {v.text if v is not None else '無（從未在 Excel 中計算）'}"
        else:
            yield ref, "數值", float(v.text)


if __name__ == "__main__":
    data = make_xlsx()
    print(f"xlsx 大小 {len(data)} bytes，內含：", zipfile.ZipFile(io.BytesIO(data)).namelist())
    for ref, kind, value in read_cells(data):
        print(f"{ref:<3} {kind}：{value}")
    print("注意 B2 是字串 '001'，不是數字 1；D3 是公式但沒有快取值，openpyxl 的 data_only=True 會讀到 None。")
