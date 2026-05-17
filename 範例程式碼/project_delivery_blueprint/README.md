# Project Delivery Blueprint Sample

此範例示範如何把 Python 教材中的多個工程主題收斂成一個可交付的 reference project，重點包含：

- configuration contract
- snapshot validation
- idempotent processing
- fail-safe alarm handling
- release evidence / update record payload

## 結構

```text
project_delivery_blueprint/
├─ README.md
├─ scripts/
│  └─ run_project_delivery_smoke.py
├─ src/
│  └─ project_delivery_blueprint/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ domain.py
│     └─ service.py
└─ tests/
   └─ test_project_delivery_blueprint.py
```

## 驗證

```bash
python3 -m py_compile src/project_delivery_blueprint/*.py scripts/run_project_delivery_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/run_project_delivery_smoke.py
```

## 這個範例在教什麼

- 怎麼把設定、領域物件與核心服務拆開
- 怎麼在同一輪處理中同時做到資料去重與告警判斷
- 怎麼產出可以直接放進更新紀錄或 release note 的 evidence
