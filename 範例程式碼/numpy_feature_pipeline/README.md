# NumPy Feature Pipeline 範例

這是 `python_numpy_engineering_tutorial.html` 的可對照專案。目的不是展示最多 NumPy API，而是示範資料工程專案需要留下的最小交付邊界：`pyproject.toml`、`src/`、`tests/`、`samples/`、CLI 與 sample data smoke test。

## 專案重點

| 檔案 | 用途 |
| --- | --- |
| `samples/features.csv` | 固定輸入資料，用於 CLI、wheel 與打包驗收。 |
| `src/numpy_feature_pipeline/pipeline.py` | 純函式資料管線：讀 CSV、驗 shape/dtype、輸出 `.npy` 與 JSON 統計。 |
| `src/numpy_feature_pipeline/cli.py` | CLI 邊界，只負責參數、路徑與輸出。 |
| `tests/test_pipeline.py` | 驗證 shape、dtype、NaN policy、統計欄位與錯誤路徑。 |

## 本機驗收

```bash
python -m pip install -e ".[test]"
pytest -q
numpy-feature-pipeline samples/features.csv --out-dir /tmp/numpy-feature-demo
```

預期輸出：

```text
wrote /tmp/numpy-feature-demo/features.npy
wrote /tmp/numpy-feature-demo/stats.json
```

## 交付檢查

- CSV 欄位順序不可只靠人工記憶，必須由 `FEATURE_COLUMNS` 與測試固定。
- 輸出矩陣 dtype 固定為 `float32`，避免平台或預設推斷造成模型輸入漂移。
- 缺值與非有限數值需 fail fast，不允許靜默寫入 `.npy`。
- wheel / PyInstaller 驗收時使用同一份 `samples/features.csv`。
