# CLI Automation Engineering Sample

這個範例示範如何用 Python 標準庫把一次性腳本整理成可交付 CLI：

- `plan`：做預檢，不產生副作用
- `apply`：支援 `--dry-run` 與實際執行
- `report`：讀取既有 JSON 證據，不重跑工作

## 結構

```text
cli_automation_engineering/
├─ src/cli_automation_engineering/
│  ├─ __init__.py
│  ├─ cli.py
│  └─ engine.py
├─ tests/test_cli_automation_engineering.py
├─ scripts/run_cli_automation_smoke.py
└─ README.md
```

## 驗證

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_cli_automation_smoke.py
```
