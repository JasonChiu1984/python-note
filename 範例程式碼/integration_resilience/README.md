# Integration Resilience Sample

這個範例示範如何用 Python 標準庫建立外部 API / gateway client 的整合韌性流程。情境是 Python service 呼叫外部設備 API、工業閘道或雲端服務時，必須明確處理 timeout、retry、idempotency、rate limit、circuit breaker、response schema validation 與 release evidence。

## Architecture

```text
business request
  -> retry / timeout policy
  -> idempotency decision
  -> rate limit check
  -> circuit breaker
  -> transport Protocol
  -> response schema validation
  -> integration evidence report
```

## Setup

```bash
cd 範例程式碼/integration_resilience
python3 -m py_compile src/integration_resilience/*.py scripts/run_integration_resilience_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_integration_resilience_smoke.py
```

## Configuration

| 設定 | 預設值 | 用途 |
|---|---:|---|
| timeout_seconds | `2.0` | 單次外部呼叫逾時預算 |
| max_attempts | `3` | 可重試 request 的最大嘗試次數 |
| backoff_seconds | `0.2` | retry backoff 基準 |
| circuit_failure_threshold | `2` | 連續失敗後開路保護 |
| rate_limit_per_minute | `60` | 避免壓垮外部 API 或現場 gateway |

## Verification

成功時會輸出：

```text
integration resilience smoke passed: retry + idempotency + circuit + schema + evidence
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| POST 被拒絕重試 | 補上 idempotency key，或把 request 改成不可重試 |
| circuit breaker 提早開啟 | 檢查外部服務 5xx / timeout 是否連續發生 |
| rate limit blocking | 調整上游 polling interval 或改用 bounded queue |
| response validation 失敗 | 確認回應 JSON 包含 `status` 與 `payload` |

## Best Practices

- timeout 是每個外部依賴的必備契約，不應使用無限等待。
- retry 只適合暫時性錯誤，且必須遵守 idempotency 規則。
- circuit breaker 是保護本服務與外部設備的 fail-safe，不是隱藏故障。
- 對 PLC/DDC/SCADA gateway，polling interval、timeout、retry 與 alarm policy 要一起設計。
