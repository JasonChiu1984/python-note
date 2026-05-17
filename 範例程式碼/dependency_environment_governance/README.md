# Dependency Environment Governance Sample

此範例示範 Python 專案如何把依賴與執行環境做成可驗證的工程邊界，涵蓋：

- `venv` 與 Python runtime baseline
- `requirements.txt`、`requirements-dev.txt`、`constraints.txt` 的治理規則
- production 依賴 pin 版本檢查
- dev 依賴引用 production requirements 的契約
- governance report、unittest 與 smoke 驗收

## 結構

```text
dependency_environment_governance/
├─ README.md
├─ requirements.txt
├─ requirements-dev.txt
├─ constraints.txt
├─ scripts/
│  └─ run_dependency_environment_governance_smoke.py
├─ src/
│  └─ dependency_environment_governance/
│     ├─ __init__.py
│     └─ policy.py
└─ tests/
   └─ test_dependency_environment_governance.py
```

## 驗證

```bash
python3 -m py_compile \
  src/dependency_environment_governance/*.py \
  scripts/run_dependency_environment_governance_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_dependency_environment_governance_smoke.py
```
