# CI Quality Gate Sample

這個範例示範如何用 Python 標準庫建立可本機執行的 CI/CD 品質閘門。它不是取代 ruff、pytest、coverage 或 GitHub Actions，而是先把 gate contract 建清楚，讓學生理解每一個檢查為什麼存在。

## Architecture

```text
source tree
  -> py_compile
  -> unittest
  -> coverage policy model
  -> runtime matrix policy
  -> workflow contract check
  -> release evidence
```

## Setup

```bash
cd 範例程式碼/ci_quality_gate
python3 -m py_compile src/ci_quality_gate/*.py scripts/run_ci_gate.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_ci_gate.py
```

## Configuration

| 設定 | 預設值 | 用途 |
|---|---|---|
| stable runtime | 3.14 | production blocking lane |
| beta runtime | 3.15 | readiness preview lane |
| coverage floor | 80 | release gate threshold |
| workflow path | `.github/workflows/python-ci.yml` | CI contract |

## Verification

成功時會輸出：

```text
ci quality gate passed: compile + tests + coverage + matrix + workflow
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| `ModuleNotFoundError` | 使用 `PYTHONPATH=src` 或直接執行 `scripts/run_ci_gate.py` |
| workflow check 失敗 | 確認 `.github/workflows/python-ci.yml` 內含 stable、beta、test、compile |
| coverage policy 失敗 | 調整測試覆蓋或降低示範門檻，但 release 前需記錄原因 |

## Best Practices

- 本機 gate 與 CI gate 使用同一組命令。
- beta preview lane 不應阻擋正式 release，但要產生相容性預警。
- release evidence 應包含版本、runtime、command、status 與失敗原因。
