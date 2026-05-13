# Observability Operations 範例專案

這個範例示範不依賴外部監控服務時，如何先用標準庫建立可觀測性 baseline：

- JSON structured log
- trace id / span event
- request count、error count、latency、dependency timeout metrics
- liveness / readiness / degraded health report
- SLO evaluation

## Setup

```bash
cd 範例程式碼/observability_operations
PYTHONPATH=src python3 -m observability_operations.demo
```

## Verification

```bash
python3 -m py_compile src/observability_operations/*.py tests/*.py scripts/run_observability_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_observability_smoke.py
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| `ModuleNotFoundError` | 確認已設定 `PYTHONPATH=src`，或從專案根目錄執行 script |
| health 顯示 `ready=fail` | 檢查 demo 是否刻意模擬 dependency timeout |
| SLO failed | 查看 metrics 中 `errors_total` 與 `average_latency_ms` |
