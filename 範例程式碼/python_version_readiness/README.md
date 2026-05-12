# Python Version Readiness

最小可讀範例：把 Python 版本升級治理做成可測試的程式碼，而不是只寫在文件裡。

## 目標

- 偵測目前 Python runtime 版本。
- 用明確 policy 判斷 3.14 / 3.15 readiness。
- 輸出 JSON readiness report，方便 CI、release note 或 canary checklist 引用。
- 不依賴第三方套件，讓範例可在乾淨 Python 環境執行。

## 使用

```bash
python -m version_readiness.cli
python -m unittest discover -s tests
```

## 專案重點

- `src/version_readiness/compat.py`：集中版本與 feature policy。
- `src/version_readiness/cli.py`：輸出可被 CI 保存的 JSON report。
- `tests/test_compat.py`：測試版本 gate 與 report 欄位，而不是測目前電腦剛好裝了哪個版本。

