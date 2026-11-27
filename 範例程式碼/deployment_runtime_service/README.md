# Deployment Runtime Service 範例

此範例用 Python 標準庫示範 production runtime contract：

- 環境變數設定與驗證
- `/healthz` 與 `/readyz`
- dependency degraded 狀態
- JSON structured logging
- SIGTERM / SIGINT 實測、停止接新連線與已接請求限時收尾
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
- 收到 SIGTERM／SIGINT 後，主迴圈關閉監聽 socket，最多等 `SHUTDOWN_TIMEOUT_SECONDS`（預設 10 秒）收尾已接收的請求。正常結束為 0；超時記錄 `shutdown_timed_out` 並以 1 結束，未完成請求可能中斷，不算完整收尾。
- Compose 的 `stop_grace_period: 12s` 是平台強制停止前的預算，須比應用程式收尾預算長。HTTP listener 很快關閉，客戶端不保證觀察到短暫的 readiness 503；若要先摘流量，須由上游協調。
- `unittest` 會在本機用子程序送 SIGTERM／SIGINT，另測試既有請求完成或超時。smoke 僅檢查設定、狀態和靜態部署檔，不代表已執行 Docker lifecycle。
