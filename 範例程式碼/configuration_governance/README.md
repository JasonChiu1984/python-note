# Configuration Governance Sample

此範例示範 Python 專案如何把多環境設定做成可驗證的工程邊界，涵蓋：

- defaults、env、secret file、CLI override 的 precedence
- typed settings 與 fail-fast validation
- secret redaction 與 config evidence report
- feature flag metadata 與 owner / expires_on
- 工業資料閘道常見的 timeout、poll interval、write enable fail-safe

## 結構

```text
configuration_governance/
├─ pyproject.toml
├─ README.md
├─ scripts/
│  └─ run_configuration_governance_smoke.py
├─ src/
│  └─ configuration_governance/
│     ├─ __init__.py
│     ├─ loader.py
│     ├─ report.py
│     └─ testing.py
└─ tests/
   └─ test_configuration_governance.py
```

## 驗證

```bash
python3 -m py_compile src/configuration_governance/*.py scripts/run_configuration_governance_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_configuration_governance_smoke.py
```
