# Batch Scheduler Engineering Sample

此範例示範 Python 專案如何把批次與排程工作做成可驗證的工程邊界，涵蓋：

- job contract
- lease / worker ownership
- checkpoint / resume
- retry budget / dead-letter
- backfill evidence、unittest 與 smoke 驗收

## 結構

```text
batch_scheduler_engineering/
├─ README.md
├─ scripts/
│  └─ run_batch_scheduler_smoke.py
├─ src/
│  └─ batch_scheduler_engineering/
│     ├─ __init__.py
│     └─ runner.py
└─ tests/
   └─ test_batch_scheduler_engineering.py
```

## 例行進度與回補分開

`last_checkpoint` 只記錄例行作業的續跑游標。指定 `backfill_from` 時，
用呼叫端提供的範圍回補，成功項目只記在本次報告的 `last_replayed_item`；
沒有成功項目時為 `None`。回補不回退也不推進例行游標。
若回補超過例行進度，下一次例行執行仍會處理那些項目，寫入端須保持冪等。

## 驗證

```bash
python3 -m py_compile \
  src/batch_scheduler_engineering/*.py \
  scripts/run_batch_scheduler_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_batch_scheduler_smoke.py
```
