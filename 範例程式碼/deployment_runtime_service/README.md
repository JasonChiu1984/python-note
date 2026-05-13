# Deployment Runtime Service 範例

此範例用 Python 標準庫示範 production runtime contract：

- 環境變數設定與驗證
- `/healthz` 與 `/readyz`
- dependency degraded 狀態
- JSON structured logging
- SIGTERM / SIGINT graceful shutdown state
- Dockerfile、Compose、`.dockerignore` 靜態部署契約

## 本機驗證

```bash
python3 -m py_compile src/deployment_runtime_service/*.py scripts/run_deployment_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_deployment_smoke.py
```

## 啟動服務

```bash
PYTHONPATH=src \
APP_NAME=deployment-runtime-service \
APP_PORT=8080 \
APP_ENV=local \
python3 -m deployment_runtime_service.server
```

## Docker 驗證邊界

本範例提供 Dockerfile 與 Compose 契約，但 smoke script 不要求本機 Docker daemon。若現場有 Docker，可額外執行：

```bash
docker build -t deployment-runtime-service:0.1.0 .
docker compose up --build
```

## 風險注意

- secret 不應寫入 image、compose 或 log。
- readiness 應包含 dependency 狀態；liveness 只表示 process 是否存活。
- rolling update 時 SIGTERM 必須能讓服務進入 draining，再於 timeout 前結束。
