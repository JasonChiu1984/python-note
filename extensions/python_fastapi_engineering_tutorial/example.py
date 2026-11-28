"""FastAPI 生產化重點：lifespan 管理資源、背景工作、統一錯誤格式（RFC 9457）、健康檢查（需 fastapi、httpx）。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

EVENTS = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = {"connected": True}          # 正式環境：建立資料庫或 Modbus 連線池
    EVENTS.append("startup")
    yield
    app.state.pool["connected"] = False
    EVENTS.append("shutdown")


app = FastAPI(lifespan=lifespan)


class DeviceOffline(Exception):
    def __init__(self, device):
        self.device = device


@app.exception_handler(DeviceOffline)
async def offline_handler(request: Request, exc: DeviceOffline):
    return JSONResponse(status_code=503, media_type="application/problem+json", headers={"Retry-After": "30"},
                        content={"type": "https://example.com/problems/device-offline", "title": "Device offline",
                                 "status": 503, "detail": f"{exc.device} 無回應", "instance": str(request.url.path)})


@app.get("/healthz")
def health(request: Request):
    ok = request.app.state.pool["connected"]
    return JSONResponse({"status": "ok" if ok else "degraded"}, status_code=200 if ok else 503)


@app.get("/devices/{dev}/value")
def value(dev: str):
    if dev.startswith("OFF"):
        raise DeviceOffline(dev)
    return {"device": dev, "value": 22.5}


if __name__ == "__main__":
    with TestClient(app) as c:                     # 進入時執行 startup，離開時執行 shutdown
        print("健康檢查：", c.get("/healthz").json())
        print("正常讀值：", c.get("/devices/AHU-01/value").json())
        r = c.get("/devices/OFF-03/value")
        print("離線設備：", r.status_code, r.headers["content-type"], r.headers["retry-after"])
        print("  ", r.json())
    print("生命週期事件：", EVENTS)
