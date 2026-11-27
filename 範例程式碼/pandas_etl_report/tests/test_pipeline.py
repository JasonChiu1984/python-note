from __future__ import annotations

import json

import pytest

from pandas_etl_report.pipeline import build_report, load_orders, write_report


def test_load_orders_validates_required_columns(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text("order_id,amount\no-001,1200\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing columns"):
        load_orders(csv_path)


def test_build_report_quality_and_revenue(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text(
        "order_id,customer_id,country,created_at,amount\n"
        "o-001,c-001,TW,2026-05-01T10:20:00+08:00,1200\n"
        "o-002,c-002,JP,2026-05-02T09:30:00+09:00,\n",
        encoding="utf-8",
    )

    report = build_report(load_orders(csv_path))

    assert report["quality"]["rows"] == 2
    assert report["quality"]["amount_missing_ratio"] == 0.5
    assert report["revenue"] == [{"country": "TW", "month": "2026-05", "revenue": 1200.0, "orders": 1}]


def test_write_report(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text(
        "order_id,customer_id,country,created_at,amount\n"
        "o-001,c-001,TW,2026-05-01T10:20:00+08:00,1200\n",
        encoding="utf-8",
    )

    output = write_report(csv_path, tmp_path / "report.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["quality"]["rows"] == 1
    assert payload["revenue"][0]["country"] == "TW"


def test_empty_report_has_null_missing_ratio(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text("order_id,customer_id,country,created_at,amount\n", encoding="utf-8")
    output = write_report(csv_path, tmp_path / "report.json")
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["quality"]["amount_missing_ratio"] is None
    assert report["revenue"] == []


def test_month_uses_utc_boundary(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text(
        "order_id,customer_id,country,created_at,amount\n"
        "o-001,c-001,TW,2026-06-01T00:05:00+08:00,20\n", encoding="utf-8"
    )
    report = build_report(load_orders(csv_path))
    assert report["revenue"][0]["month"] == "2026-05"


def test_csv_missing_markers_are_column_contracts(tmp_path: Path) -> None:
    csv_path = tmp_path / "country-sentinels.csv"
    csv_path.write_text(
        "order_id,customer_id,country,created_at,amount\n"
        "0007,c1,NA,2026-06-01T00:00:00Z,20\n"
        "NULL,c2,,2026-06-02T00:00:00Z,5\n"
        "0009,c3,TW,2026-06-03T00:00:00Z,\n",
        encoding="utf-8",
    )
    orders = load_orders(csv_path)
    assert orders["order_id"].tolist() == ["0007", "NULL", "0009"]
    assert orders["country"].isna().tolist() == [False, True, False]
    report = build_report(orders)
    assert report["quality"] == {"rows": 3, "amount_missing_ratio": 0.3333, "countries": ["NA"]}
    assert report["revenue"] == [
        {"country": "NA", "month": "2026-06", "revenue": 20.0, "orders": 1},
        {"country": None, "month": "2026-06", "revenue": 5.0, "orders": 1},
    ]
