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

## SLO 判定與展示是兩件事

`evaluate_slo()` 先用未四捨五入的錯誤率與平均延遲判斷，兩個上限皆含等號。回傳 `status` 為 `pass`、`fail` 或 `no_data`，只有 `pass` 時 `passed` 才為 `true`；`evaluated` 保留實際比較值，沒有樣本時是 `null`。顯示用 `metrics` 仍會四捨五入，空窗口的顯示欄位為 0；不得把這些值拿來覆核門檻或當作健康證明。此程式只示範平均延遲及錯誤率，正式服務還需定義合格事件、樣本窗、延遲分位數或符合單筆門檻的比率。

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| `ModuleNotFoundError` | 確認已設定 `PYTHONPATH=src`，或從專案根目錄執行 script |
| health 顯示 `ready=fail` | 檢查 demo 是否刻意模擬 dependency timeout |
| SLO `fail`／`no_data` | 看 `status` 及未四捨五入的 `evaluated`，查流量、錯誤及延遲；`no_data` 時確認是否無流量或遙測漏收 |
