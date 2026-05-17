# Workflow State Machine Engineering Sample

此範例示範 Python 專案如何把多步驟流程做成可驗證的狀態機工程邊界，涵蓋：

- state transition contract
- guard / invariant
- timeout / expiry
- compensation / rollback
- manual review、audit trail、unittest 與 smoke 驗收

## 結構

```text
workflow_state_machine_engineering/
├─ README.md
├─ scripts/
│  └─ run_workflow_state_machine_smoke.py
├─ src/
│  └─ workflow_state_machine_engineering/
│     ├─ __init__.py
│     └─ engine.py
└─ tests/
   └─ test_workflow_state_machine_engineering.py
```

## 驗證

```bash
python3 -m py_compile \
  src/workflow_state_machine_engineering/*.py \
  scripts/run_workflow_state_machine_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_workflow_state_machine_smoke.py
```
