# FastAPI 合成機房遙測實驗

只限本機。資料不會持久化，沒有正式認證，不接現場設備。開發 CLI、執行服務和容器測試都請只對本機開放。需要 Python 3.12 以上。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
python -m pytest -q
fastapi dev --host 127.0.0.1
```

換終端機使用：

```sh
curl -fsS http://127.0.0.1:8000/health/ready
curl -fsS -X POST http://127.0.0.1:8000/v1/readings \
  -H 'Content-Type: application/json' \
  -d '{"device":"CHW01","temperature_c":7.25,"observed_at":"2026-11-25T17:00:00+08:00"}'
curl -fsS 'http://127.0.0.1:8000/v1/readings?device=CHW01&limit=10'
```

停止開發服務後，可用 `fastapi run --host 127.0.0.1` 啟動無 reload 的本機執行模式。
輪子建置及乾淨環境重驗：

```sh
python -m build --wheel
python3 -m venv /tmp/telemetry-wheel-test
/tmp/telemetry-wheel-test/bin/pip install dist/*.whl
(cd /tmp && /tmp/telemetry-wheel-test/bin/python -m uvicorn telemetry_api.main:app --host 127.0.0.1 --port 8000)
```

Docker 測試需 Docker daemon：先建 wheel 再執行 `docker build -t python-note-telemetry .`，
最後 `docker run --rm -p 127.0.0.1:8000:8000 python-note-telemetry`。
僅作為容器封裝範例，不是正式環境配方。正式部署要加 TLS、驗權、秘密管理、持久儲存、
資源限制及監控。此專案使用記憶體 Repository，不可用多 worker 當共享狀態使用。
