# Performance and Memory Engineering Sample

這個範例示範如何用 Python 標準庫建立可重現的效能與記憶體工程流程。情境是 Python service 或資料處理 pipeline 需要在 release 前留下 benchmark baseline、CPU hotspot、memory peak 與 regression budget evidence。

## Architecture

```text
workload
  -> baseline implementation
  -> optimized implementation
  -> benchmark median
  -> cProfile hotspot
  -> tracemalloc peak memory
  -> performance budget decision
  -> release evidence report
```

## Setup

```bash
cd 範例程式碼/performance_memory_engineering
python3 -m py_compile src/performance_memory_engineering/*.py scripts/run_performance_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_performance_smoke.py
```

## Configuration

| 設定 | 預設值 | 用途 |
|---|---:|---|
| dataset_size | `1200` | 固定 workload 規模 |
| max_latency_ratio | `1.15` | CI smoke 可接受的最大延遲回退比例 |
| max_peak_kib | `512` | Python allocation peak 預算 |
| profile_top_n | `5` | profile report 保留的 top function 數 |

## Verification

成功時會輸出：

```text
performance memory smoke passed: benchmark + profile + tracemalloc + budget
```

並產生：

```text
performance_evidence.json
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| benchmark 浮動 | 增加 iterations、固定資料集、使用 median |
| optimized 結果錯誤 | 先比對 slow path 與 optimized path 輸出 |
| profile 找不到熱點 | 增加 workload 或改用更接近 production 的資料分布 |
| memory peak 超標 | 檢查暫存 list/dict、chunk size、streaming 策略 |

## Best Practices

- 沒有 baseline 不做效能結論。
- 沒有正確性 regression test 不做效能優化。
- `cProfile` 適合 CPU hotspot，`tracemalloc` 適合 Python allocation hotspot。
- CI 中只擋明顯回退；正式容量結論需固定機器、資料量與多次測量。
