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

## 驗證

```bash
python3 -m py_compile \
  src/batch_scheduler_engineering/*.py \
  scripts/run_batch_scheduler_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_batch_scheduler_smoke.py
```
