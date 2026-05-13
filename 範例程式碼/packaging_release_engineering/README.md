# Packaging Release Engineering Sample

這個範例示範 Python 專案發布前的最小可驗收 release gate。範例只使用標準庫，重點是把 package metadata、版本契約、changelog、source archive、checksum 與 manifest 做成可重跑流程。

## Architecture

```text
pyproject.toml
  |
  +--> package __version__
  +--> CHANGELOG.md
  +--> source files
          |
          v
release gate
  |
  +--> deterministic tar.gz
  +--> SHA-256 checksum
  +--> release-manifest.json
```

## Setup

不需要第三方套件：

```bash
cd 範例程式碼/packaging_release_engineering
python3 -m py_compile src/packaging_release_engineering/*.py scripts/run_release_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_release_smoke.py
```

## Verification

測試覆蓋：

- `pyproject.toml` 專案名稱與版本存在
- package `__version__` 與 project version 一致
- `CHANGELOG.md` 有對應 `v<version>` 條目
- source archive 不包含 `dist/`、`__pycache__`、`.pyc`
- manifest 會記錄 artifact、checksum、檔案清單與 gate 狀態

## Troubleshooting

| 問題 | 原因 | 處理方式 |
|---|---|---|
| `ModuleNotFoundError` | 沒設定 `PYTHONPATH` | 使用 `PYTHONPATH=src ...` 或執行 smoke script |
| `Version mismatch` | `pyproject.toml` 與 package `__version__` 不一致 | 同步兩處版本後重跑 release gate |
| `Missing changelog entry` | `CHANGELOG.md` 沒有對應版本 | 新增 `## vX.Y.Z - YYYY-MM-DD` |
| manifest checksum 不一致 | artifact 被重新產生或檔案內容改變 | 重新產生 manifest 並確認 Git diff |

## Best Practices

- 發布前先驗證 metadata、版本與 changelog，再建立 artifact。
- artifact 建立後要產生 checksum 與 manifest，避免只相信檔名。
- CI 應保留 release gate log、test result 與 manifest。
- PyPI/GitHub Release 屬於外部發布步驟，本地 gate 應先通過再推送。
