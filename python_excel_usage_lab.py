"""Create, read and analyze a synthetic workbook in a temporary directory."""
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo


def make_report(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "點表"
    # [寫入] append 新增列；cell 與 A1 可直接定點存取。
    ws.append(["ID", "溫度", "時間", "狀態", "合成公式"])
    ws.append(["0012", 7.125, datetime(2026, 11, 25, 9), "正常", "=B2*2"])
    ws.cell(row=3, column=1, value="0048")
    ws["B3"] = 10
    ws["C3"] = datetime(2026, 11, 25, 10)
    ws["D3"] = "待查"

    # [樣式] 顯示規則不改值。
    line = Side(style="thin", color="FFD4DFEB")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFFFF")
        cell.fill = PatternFill(fill_type="solid", fgColor="FF285B82")
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = Border(bottom=line)
    for cell in ws["B"][1:]:
        cell.number_format = '0.00" °C"'
    for cell in ws["C"][1:]:
        cell.number_format = "yyyy-mm-dd hh:mm"
    ws.freeze_panes = "B2"

    # [結構] Table 有自己的篩選；獨立工作表用 worksheet.auto_filter。
    table = Table(displayName="HVACPoints", ref="A1:E3")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2",
                                         showRowStripes=True)
    ws.add_table(table)
    checks = wb.create_sheet("複核")
    checks.append(["ID", "狀態"])
    checks.append(["0048", "待查"])
    checks.auto_filter.ref = "A1:B2"
    checks.auto_filter.add_filter_column(1, ["待查"])

    # [規則] 資料驗證和條件格式是 Excel 用戶端規則。
    rule = DataValidation(type="list", formula1='"正常,待查"',
                          allow_blank=False, showErrorMessage=True)
    rule.errorTitle = "狀態不符"
    rule.error = "請選正常或待查"
    ws.add_data_validation(rule)
    rule.add("D2:D20")
    ws.conditional_formatting.add(
        "B2:B20",
        CellIsRule(operator="greaterThan", formula=["9"],
                   fill=PatternFill(fill_type="solid", fgColor="FFFFDFAD")),
    )
    with path.open("xb") as dest:
        wb.save(dest)
    wb.close()


def inspect_report(path):
    # [讀取] 用迭代器限定範圍，分別驗證公式文本與快取。
    book = load_workbook(path, data_only=False)
    try:
        ws = book["點表"]
        values = list(ws.iter_rows(min_row=2, max_row=3,
                                   min_col=1, max_col=2, values_only=True))
        assert values == [("0012", 7.125), ("0048", 10)]
        assert ws.cell(row=2, column=1).value == ws["A2"].value == "0012"
        assert ws["A2:B3"][1][1].value == 10
        assert ws["B2"].number_format == '0.00" °C"'
        assert ws["A1"].font.bold and ws["A1"].fill.patternType == "solid"
        assert ws["A1"].alignment.wrap_text and ws["A1"].border.bottom.style == "thin"
        assert ws.freeze_panes == "B2"
        assert ws.tables["HVACPoints"].ref == "A1:E3"
        assert book["複核"].auto_filter.filterColumn[0].colId == 1
        assert str(ws.data_validations.dataValidation[0].sqref) == "D2:D20"
        assert len(ws.conditional_formatting) == 1
        assert ws["E2"].data_type == "f" and ws["E2"].value == "=B2*2"
    finally:
        book.close()
    cached = load_workbook(path, read_only=True, data_only=True)
    try:
        # A new openpyxl-written formula has no recalculated value.
        assert cached["點表"]["E2"].value is None
    finally:
        cached.close()


def stream_report(path):
    # [大檔] 寫入模式先配置，逐列產生；再以唯讀模式驗證尾端。
    out = Workbook(write_only=True)
    ws = out.create_sheet("序列")
    ws.freeze_panes = "A2"
    ws.append(["索引", "讀值"])
    for i in range(1, 1001):
        value = WriteOnlyCell(ws, value=i / 10)
        value.number_format = "0.0"
        ws.append([i, value])
    with path.open("xb") as dest:
        out.save(dest)
    incoming = load_workbook(path, read_only=True)
    try:
        last = None
        for last in incoming["序列"].iter_rows(min_row=2, max_col=2, values_only=True):
            pass
        assert last == (1000, 100.0)
    finally:
        incoming.close()


def analyze_with_pandas(path):
    import pandas as pd

    # [分析] 清理值及統計；不覆寫原工作簿。
    frame = pd.read_excel(path, sheet_name="點表",
                          usecols=["ID", "溫度", "狀態"],
                          dtype={"ID": "string"}, engine="openpyxl",
                          keep_default_na=False)
    frame["溫度"] = pd.to_numeric(frame["溫度"], errors="coerce")
    assert frame["ID"].tolist() == ["0012", "0048"]
    assert frame["ID"].is_unique and frame["溫度"].between(-50, 100).all()
    result = frame.groupby("狀態", dropna=False)["溫度"].agg(["count", "mean"])
    assert result.loc["正常", "count"] == 1
    assert result.loc["待查", "mean"] == 10.0


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    args = parser.parse_args()
    if not __debug__:
        parser.error("run without -O to execute assertions")
    with TemporaryDirectory(prefix="excel-usage-") as directory:
        base = Path(directory)
        report = base / "report.xlsx"
        make_report(report)
        inspect_report(report)
        stream_report(base / "stream.xlsx")
        if args.pandas:
            analyze_with_pandas(report)
    print("PASS workbook values, styles, table, validation, formulas, and streaming"
          + (" + pandas" if args.pandas else ""))


if __name__ == "__main__":
    main()
