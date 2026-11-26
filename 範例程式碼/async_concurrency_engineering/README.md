# Async Concurrency Engineering Sample

這個範例示範 Python 標準庫 `asyncio` 在 Python 3.11 以上的離線 worker 管線。佇列及結果在記憶體，只用於有限批次；沒有持久化或接收端去重。

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
  +-- admission deadline, end-to-end budget and per-attempt timeout
  +-- retry for retryable error
  +-- permanent error classification
  +-- supervised drain; abort cancels and awaits worker cleanup
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
- 正常關機先停止 producer 再排空；worker 非預期失敗會回報原始例外並中止。
- 排空逾時會取消並等待合作清理；期限耗盡後不再啟動下一次嘗試。
- 10 個測試案例覆蓋正常、重試、期限、滿載與中止。

## Troubleshooting

| 問題 | 原因 | 處理方式 |
|---|---|---|
| `ModuleNotFoundError` | 沒設定 `PYTHONPATH` | 使用 `PYTHONPATH=src ...` 或執行 smoke script |
| 測試卡住 | handler 沒有 timeout 或 queue 沒 drain | 檢查 `per_item_timeout` 與 `await pipeline.close()` |
| worker 未停止 | sentinel 沒送到每個 worker | 確認 `worker_count` 與 shutdown 流程 |

## Best Practices

- 對外部 I/O 一律設定 timeout。
- queue 要有 `maxsize`，避免 producer 無限制吃掉記憶體。
- cancellation 要能向上傳遞，不要攔截後壓掉 `CancelledError`；在 finally 清理後向上傳遞。
- retry 只處理安全可重送的操作；`idempotency_key` 欄位本身不會去重。
- `close()` 或 `abort()` 前，呼叫端先停止並等待自己啟動的所有 producer。
