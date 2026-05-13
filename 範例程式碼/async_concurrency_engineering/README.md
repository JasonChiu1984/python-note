# Async Concurrency Engineering Sample

這個範例示範 Python 標準庫 `asyncio` 在 production worker pipeline 中的最小可驗收形狀。

## Architecture

```text
producer
  |
  v
bounded asyncio.Queue
  |
  v
worker tasks
  |
  +-- per-item timeout
  +-- retry for retryable error
  +-- permanent error classification
  +-- cancellation-safe shutdown
  |
  v
results + metrics
```

## Setup

不需要第三方套件：

```bash
cd 範例程式碼/async_concurrency_engineering
python3 -m py_compile src/async_concurrency_engineering/*.py scripts/run_async_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_async_smoke.py
```

## Verification

測試覆蓋：

- worker pool 正常處理多筆 work item
- retryable error 會重試後成功
- timeout 會被分類並記錄
- bounded queue 會形成 backpressure
- shutdown 會等待 queue drain 後停止 worker

## Troubleshooting

| 問題 | 原因 | 處理方式 |
|---|---|---|
| `ModuleNotFoundError` | 沒設定 `PYTHONPATH` | 使用 `PYTHONPATH=src ...` 或執行 smoke script |
| 測試卡住 | handler 沒有 timeout 或 queue 沒 drain | 檢查 `per_item_timeout` 與 `await pipeline.close()` |
| worker 未停止 | sentinel 沒送到每個 worker | 確認 `worker_count` 與 shutdown 流程 |

## Best Practices

- 對外部 I/O 一律設定 timeout。
- queue 要有 `maxsize`，避免 producer 無限制吃掉記憶體。
- cancellation 要能向上傳遞，不要用寬泛 `except Exception` 吃掉。
- retry 只處理可重試錯誤，永久錯誤要快速失敗並留下證據。
