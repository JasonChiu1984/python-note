# Architecture Governance Sample

此範例示範 Python 專案如何把架構治理做成可驗證的工程邊界，涵蓋：

- `ADR` 決策紀錄
- module ownership
- import boundary rule
- deprecation policy 與 sunset date
- governance report、unittest 與 smoke 驗收

## 結構

```text
architecture_governance/
├─ README.md
├─ architecture_decisions.md
├─ module_ownership.json
├─ import_rules.json
├─ scripts/
│  └─ run_architecture_governance_smoke.py
├─ src/
│  └─ architecture_governance/
│     ├─ __init__.py
│     └─ policy.py
└─ tests/
   └─ test_architecture_governance.py
```

## 驗證

```bash
python3 -m py_compile \
  src/architecture_governance/*.py \
  scripts/run_architecture_governance_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_architecture_governance_smoke.py
```
