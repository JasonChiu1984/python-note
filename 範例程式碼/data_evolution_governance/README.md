# Data Evolution Governance Sample

這個範例示範 Python 專案如何用標準庫做資料演進治理：

- schema version manifest
- v1 -> v2 相容讀取
- expand / contract discipline
- backfill checkpoint / resume
- drift preflight
- rollback read 驗證
- migration report evidence

## 執行

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_data_evolution_smoke.py
```
