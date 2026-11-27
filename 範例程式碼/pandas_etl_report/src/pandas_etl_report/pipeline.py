from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {"order_id", "customer_id", "country", "created_at", "amount"}


def load_orders(csv_path: Path) -> pd.DataFrame:
    orders = pd.read_csv(
        csv_path,
        keep_default_na=False,
        # 只把契約欄位的空欄當缺值。NA 國別碼與 NULL 識別碼可合法存在。
        na_values={column: [""] for column in REQUIRED_COLUMNS},
        dtype={
            "order_id": "string",
            "customer_id": "string",
            "country": "string",
            "amount": "float64",
        },
    )
    missing = REQUIRED_COLUMNS - set(orders.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    orders["created_at"] = pd.to_datetime(orders["created_at"], utc=True, errors="raise")
    return orders


def build_report(orders: pd.DataFrame) -> dict[str, Any]:
    amount_missing_ratio = round(float(orders["amount"].isna().mean()), 4) if len(orders) else None
    clean = orders.loc[orders["amount"].notna()].copy()
    if clean["amount"].isin([float("inf"), float("-inf")]).any():
        raise ValueError("amount must be finite")
    clean["month"] = clean["created_at"].dt.strftime("%Y-%m")

    revenue = (
        clean.groupby(["country", "month"], dropna=False)
        .agg(revenue=("amount", "sum"), orders=("order_id", "nunique"))
        .reset_index()
        .sort_values(["country", "month"])
    )

    return {
        "quality": {
            "rows": int(len(orders)),
            "amount_missing_ratio": amount_missing_ratio,
            "countries": sorted(clean["country"].dropna().unique().tolist()),
        },
        "revenue": revenue.astype(object).where(revenue.notna(), None).to_dict(orient="records"),
    }


def write_report(csv_path: Path, output_path: Path) -> Path:
    report = build_report(load_orders(csv_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return output_path
