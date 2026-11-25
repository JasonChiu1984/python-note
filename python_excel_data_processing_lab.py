"""以合成 HVAC 點表示範 .xlsx：寫入、框線、Excel 表格、讀回驗證。"""
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from math import isfinite
from statistics import mean
from pathlib import Path
from tempfile import NamedTemporaryFile

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

HEADER = ("點位 ID", "設備", "讀值", "量測時間", "超過 24°C")
ROWS = (
    ("001", "AHU-01", 22.5, datetime(2026, 11, 25, 8, 30)),
    ("002", "AHU-02", 25.2, datetime(2026, 11, 25, 8, 31)),
    ("003", "AHU-03", 23.0, datetime(2026, 11, 25, 8, 32)),
)


def summarize(rows):
    """回傳各設備有效筆數、平均、最大及超門檻次數；另列拒絕筆數。"""
    groups = defaultdict(list)
    rejected = 0
    for _, equipment, value, measured_at in rows:
        key = equipment.strip().upper() if isinstance(equipment, str) else ""
        if (not key or type(value) not in (int, float) or not isfinite(value)
                or not -40 <= value <= 100 or not isinstance(measured_at, datetime)):
            rejected += 1
            continue
        groups[key].append(value)
    return [(key, len(vals), round(mean(vals), 2), max(vals),
             sum(v > 24 for v in vals)) for key, vals in sorted(groups.items())], rejected


def write_report(path: Path) -> None:
    if path.suffix.lower() != ".xlsx":
        raise ValueError("輸出副檔名必須是 .xlsx")
    if path.exists():
        raise FileExistsError(path)
    wb = Workbook()
    ws = wb.active
    ws.title = "HVAC點表"
    ws.append(HEADER)
    for n, row in enumerate(ROWS, start=2):
        ws.append((*row, f"=C{n}>24"))
        ws[f"A{n}"].number_format = "@"
        ws[f"C{n}"].number_format = "0.0"
        ws[f"D{n}"].number_format = "yyyy-mm-dd hh:mm"
    table = Table(displayName="HvAcReadings", ref=f"A1:E{ws.max_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True
    )
    ws.add_table(table)
    line = Side(style="thin", color="FF9AACBF")
    border = Border(left=line, right=line, top=line, bottom=line)
    for row in ws.iter_rows():
        for cell in row:
            cell.border = border
            if cell.row == 1:
                cell.font = Font(bold=True, color="FFFFFFFF")
                cell.fill = PatternFill("solid", fgColor="FF174575")
                cell.alignment = Alignment(horizontal="center")
    for column, width in zip("ABCDE", (14, 16, 13, 23, 18)):
        ws.column_dimensions[column].width = width
    ws.freeze_panes = "A2"

    analysis = wb.create_sheet("分析摘要")
    summary, rejected = summarize(ROWS)
    analysis.append(("設備", "有效筆數", "平均 °C", "最大 °C", "超過 24°C 次數"))
    for row in summary:
        analysis.append(row)
    bottom = analysis.max_row
    summary_table = Table(displayName="HvAcSummary", ref=f"A1:E{bottom}")
    summary_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True
    )
    analysis.add_table(summary_table)
    for row in analysis.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row:
            cell.number_format = "0.00"
    analysis["G1"] = "拒絕資料列"
    analysis["H1"] = rejected
    chart = BarChart()
    chart.title = "各設備平均溫度"
    chart.y_axis.title = "溫度（°C）"
    chart.add_data(Reference(analysis, min_col=3, min_row=1, max_row=bottom),
                   titles_from_data=True)
    chart.set_categories(Reference(analysis, min_col=1, min_row=2, max_row=bottom))
    analysis.add_chart(chart, "G3")

    # 先在同一資料夾寫暫存，再以硬連結發佈；目的檔已存在時不覆蓋。
    # 若所在檔案系統不支援硬連結，會報錯並清除暫存。
    with NamedTemporaryFile(dir=path.parent, suffix=".xlsx", delete=False) as fp:
        temp = Path(fp.name)
    try:
        wb.save(temp)
        path.hardlink_to(temp)
    finally:
        temp.unlink(missing_ok=True)
        wb.close()


def read_and_check(path: Path) -> list[tuple]:
    wb = load_workbook(path, data_only=False)
    try:
        ws = wb["HVAC點表"]
        assert tuple(cell.value for cell in ws[1]) == HEADER
        actual = list(ws.iter_rows(min_row=2, values_only=True))
        assert [row[:4] for row in actual] == list(ROWS)
        assert all(isinstance(row[3], datetime) for row in actual)
        assert ws["A2"].data_type == "s" and ws["A2"].value == "001"
        assert ws["C2"].data_type == "n" and ws["C2"].value == 22.5
        assert ws["E2"].data_type == "f" and ws["E2"].value == "=C2>24"
        assert ws["A1"].border.bottom.style == "thin"
        assert ws["D3"].border.left.style == "thin"
        assert ws.tables["HvAcReadings"].ref == "A1:E4"
        summary, rejected = summarize(ROWS)
        analysis = wb["分析摘要"]
        assert list(analysis.iter_rows(min_row=2, max_col=5,
                                       values_only=True)) == summary
        assert analysis["H1"].value == rejected == 0
        assert analysis.tables["HvAcSummary"].ref == "A1:E4"
        assert analysis["C2"].number_format == "0.00"
        dirty = (("004", " ahu-01 ", 24.5, ROWS[0][3]),
                 ("005", "AHU-01", "25.5", ROWS[0][3]))
        dirty_summary, dirty_count = summarize((*ROWS, *dirty))
        assert dirty_summary[0] == ("AHU-01", 2, 23.5, 24.5, 1)
        assert dirty_count == 1
        return actual
    finally:
        wb.close()


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("hvac_readings.xlsx"))
    args = parser.parse_args()
    write_report(args.output)
    print("讀回驗證通過；資料列（含公式文字）：")
    for row in read_and_check(args.output):
        print(row)
