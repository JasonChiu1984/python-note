# Event Reliability Sample

這個範例示範如何用 Python 標準庫建立事件驅動可靠性流程。情境是應用服務先寫入主資料與 outbox，再由 dispatcher 將事件送往 broker，consumer 以 idempotency 保護副作用，poison message 則進入 DLQ，修正後可執行 replay。

## Architecture

```text
business change
  -> transactional outbox
  -> dispatcher
  -> broker publish
  -> idempotent consumer
  -> DLQ isolation
  -> replay after fix
  -> reliability evidence report
```

## Setup

```bash
cd 範例程式碼/event_reliability
python3 -m py_compile src/event_reliability/*.py scripts/run_event_reliability_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_event_reliability_smoke.py
```

## Configuration

| 設定 | 預設值 | 用途 |
|---|---:|---|
| `max_delivery_attempts` | `3` | 發送或消費失敗後，移入 DLQ 前的最大嘗試次數 |
| `dispatch_batch_size` | `50` | 每輪 dispatcher 處理的 pending event 上限 |
| `stream_key` | 事件自帶 | 同一資料流的順序識別，例如訂單或設備命令 |
| `replay_reason` | 手動提供 | 記錄為何將 DLQ 事件重放 |

## Verification

成功時會輸出：

```text
event reliability smoke passed: outbox + dedup + dlq + replay + evidence
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| pending outbox 一直不清 | 檢查 broker 是否可用，以及 dispatcher 是否持續執行 |
| consumer 重複套用副作用 | 確認 `event_id` 穩定且 processed set 有保留 |
| DLQ 持續增加 | 追查 schema drift、handler bug 或壞資料來源 |
| replay 又失敗 | 先修正 handler 或資料，再附帶 `replay_reason` 重新重放 |

## Best Practices

- outbox、consumer、DLQ、replay 應分開責任，不要把所有邏輯塞進同一個 worker。
- 事件 schema 要版本化，避免 consumer 與 producer 演進失控。
- 工業場域的命令事件需確認重送是否安全，必要時改用人工確認或 fail-safe。
- 發版紀錄應引用可靠性報告中的 dispatch、duplicate、DLQ 與 replay 統計。
