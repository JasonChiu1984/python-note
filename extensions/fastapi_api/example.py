"""FastAPI：Pydantic 驗證、相依注入替換、ETag 條件更新，全部用 TestClient 在記憶體中測試（需 fastapi、httpx）。"""
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


class Setpoint(BaseModel):
    value: Annotated[float, Field(ge=5.0, le=15.0, description="冰水出水溫度 °C")]


class Store:
    def __init__(self):
        self.data = {"CH-01": {"value": 7.0, "version": 1}}


def get_store() -> Store:                       # 正式環境可能連資料庫或 BACnet 閘道
    raise RuntimeError("測試中應被替換")


app = FastAPI()


@app.get("/chillers/{cid}/setpoint")
def read(cid: str, response: Response, store: Store = Depends(get_store)):
    item = store.data.get(cid) or HTTPException(404, "unknown chiller")
    if isinstance(item, HTTPException):
        raise item
    response.headers["ETag"] = f'"{item["version"]}"'
    return {"chiller": cid, "value": item["value"]}


@app.put("/chillers/{cid}/setpoint")
def write(cid: str, body: Setpoint, response: Response, store: Store = Depends(get_store),
          if_match: Annotated[str | None, Header()] = None):
    item = store.data.get(cid)
    if item is None:
        raise HTTPException(404, "unknown chiller")
    if if_match is None:
        raise HTTPException(428, "需要 If-Match，避免覆寫他人變更")
    if if_match != f'"{item["version"]}"':
        raise HTTPException(412, "版本已變更，請重新讀取")
    item.update(value=body.value, version=item["version"] + 1)
    response.headers["ETag"] = f'"{item["version"]}"'
    return {"chiller": cid, "value": item["value"]}


if __name__ == "__main__":
    store = Store()
    app.dependency_overrides[get_store] = lambda: store
    c = TestClient(app)
    r = c.get("/chillers/CH-01/setpoint")
    etag = r.headers["ETag"]
    print("GET", r.status_code, r.json(), "ETag", etag)
    print("PUT 無 If-Match", c.put("/chillers/CH-01/setpoint", json={"value": 8.0}).status_code)
    r = c.put("/chillers/CH-01/setpoint", json={"value": 8.0}, headers={"If-Match": etag})
    print("PUT 正確版本", r.status_code, r.json(), "新 ETag", r.headers["ETag"])
    print("PUT 舊版本  ", c.put("/chillers/CH-01/setpoint", json={"value": 9.0}, headers={"If-Match": etag}).status_code)
    bad = c.put("/chillers/CH-01/setpoint", json={"value": 25.0}, headers={"If-Match": r.headers["ETag"]})
    print("PUT 超出範圍", bad.status_code, bad.json()["detail"][0]["msg"])
    print("GET 不存在 ", c.get("/chillers/CH-99/setpoint").status_code)
