"""不用第三方套件解析 HTML 表格：html.parser ＋ re 驗證欄位格式，並偵測版型變動。需 Python 3.15（re.prefixmatch）。"""
import re
from html.parser import HTMLParser

SAMPLE_V1 = """<table id="aqi"><tr><th>測站</th><th>AQI</th><th>PM2.5</th><th>發布時間</th></tr>
<tr><td>中山</td><td>42</td><td>11</td><td>2026-11-28 10:00</td></tr>
<tr><td>松山</td><td>57</td><td>18</td><td>2026-11-28 10:00</td></tr>
<tr><td>古亭</td><td>—</td><td>設備維護</td><td>2026-11-28 10:00</td></tr></table>"""
SAMPLE_V2 = SAMPLE_V1.replace("<th>PM2.5</th>", "<th>PM2.5 (μg/m3)</th>")   # 網站改了欄名

EXPECTED = ["測站", "AQI", "PM2.5", "發布時間"]
TS = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def extract(html):
    p = TableParser()
    p.feed(html)
    header, *body = p.rows
    if header != EXPECTED:
        raise ValueError(f"版型變動：欄位 {header}")
    good, rejected = [], []
    for name, aqi, pm, ts in body:
        if re.fullmatch(r"\d{1,3}", aqi) and re.fullmatch(r"\d{1,4}", pm) and TS.fullmatch(ts):
            good.append({"site": name, "aqi": int(aqi), "pm25": int(pm), "ts": ts})
        else:
            rejected.append(name)
    return good, rejected


if __name__ == "__main__":
    good, rejected = extract(SAMPLE_V1)
    for g in good:
        print(g)
    print("格式不符而排除：", rejected)
    try:
        extract(SAMPLE_V2)
    except ValueError as e:
        print(e)
    print("prefixmatch 判斷是否為時間開頭：", bool(re.prefixmatch(r"\d{4}-", "2026-11-28 10:00")))
