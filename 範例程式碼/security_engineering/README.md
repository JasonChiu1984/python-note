# Security Engineering 範例專案

這個範例示範不依賴外部服務時，如何先用 Python 標準庫建立安全工程 baseline：

- PBKDF2 password hashing
- constant-time token comparison
- deny-by-default RBAC policy
- input validation and safe error response
- redacted audit log
- simple rate limiter
- dependency manifest gate

## Setup

```bash
cd 範例程式碼/security_engineering
PYTHONPATH=src python3 -m security_engineering.demo
```

## Verification

```bash
python3 -m py_compile src/security_engineering/*.py tests/*.py scripts/run_security_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_security_smoke.py
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| `ModuleNotFoundError` | 確認已設定 `PYTHONPATH=src`，或從專案根目錄執行 script |
| password verify failed | 確認 demo 使用同一組 encoded hash 與原始測試密碼 |
| policy denied | 檢查 role、action、resource 是否存在於 `RolePolicy` |
| manifest gate failed | 檢查 manifest 是否缺少 `name`、`version`、`hash` |
