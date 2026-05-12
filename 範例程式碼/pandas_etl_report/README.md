# Pandas ETL Report 範例

這是 `python_pandas_engineering_tutorial.html` 的可對照專案。它把 Pandas 教材中的 schema、missing policy、groupby、JSON feed、quality summary 與 CLI 打包收斂成一個最小可讀範例。

## 專案重點

| 檔案 | 用途 |
| --- | --- |
| `samples/orders.csv` | 固定輸入資料，用於 CLI、wheel 與打包驗收。 |
| `src/pandas_etl_report/pipeline.py` | 純函式 ETL：讀 CSV、驗欄位、處理日期、輸出營收摘要與品質摘要。 |
| `src/pandas_etl_report/cli.py` | CLI 邊界，只負責參數、路徑與輸出。 |
| `tests/test_pipeline.py` | 驗證 schema、missing policy、quality summary 與 JSON feed。 |

## 本機驗收

```bash
python -m pip install -e ".[test]"
pytest -q
pandas-etl-report samples/orders.csv --out /tmp/orders-report.json
```

預期輸出：

```text
wrote /tmp/orders-report.json
```

## 交付檢查

- 必要欄位缺失時 fail fast，不允許產生錯誤報表。
- `created_at` 統一轉成 UTC datetime，再產生月份欄位。
- `amount` 缺值列不進營收，但品質摘要要保留缺值比例。
- JSON feed 欄位名稱需由測試固定，避免 dashboard 介面被破壞。
