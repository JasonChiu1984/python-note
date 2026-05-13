# Testing Quality Gate 範例

這個範例示範 Python 測試工程的最小可驗收閉環，全部使用標準庫，方便在乾淨環境直接執行。

## Architecture

```text
testing_quality_gate/
├─ src/testing_quality_gate/
│  ├─ domain.py        # Order / OrderLine domain model
│  ├─ repository.py    # In-memory fake repository
│  ├─ service.py       # OrderService business rules
│  └─ demo.py          # release smoke entrypoint
├─ tests/
│  ├─ test_order_service.py
│  └─ test_quality_gate.py
└─ scripts/
   └─ run_quality_gate.py
```

## Workflow

1. `py_compile` 檢查所有 Python 檔案語法。
2. `unittest discover` 執行業務規則、錯誤路徑、冪等與 gate script 測試。
3. `demo.py` 作為 release smoke，證明主要入口可啟動。

## Verification

```bash
PYTHONPATH=src python3 -m testing_quality_gate.demo
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_quality_gate.py
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| `ModuleNotFoundError` | 確認從本資料夾執行，或設定 `PYTHONPATH=src` |
| gate 失敗 | 先看 stdout/stderr 中是哪個步驟失敗：compile 或 unittest |
| 測試不穩定 | 檢查是否引入真實時間、共享全域狀態或工作目錄污染 |

## Best Practices

- 先用標準庫建立可重現 baseline，再逐步加入 pytest、coverage、ruff、mypy。
- 測試名稱要能在 CI log 中直接說明壞掉的行為。
- release note 應列出實際 gate 命令與結果。
