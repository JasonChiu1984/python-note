"""前端資料流的後端支援：Server-Sent Events（SSE）格式、事件 ID 續傳與節流（標準函式庫）。

瀏覽器以 EventSource 連線，斷線重連時會帶 Last-Event-ID，伺服器從下一筆開始補送。
"""
import json

EVENTS = [(i, {"point": "AHU1_SAT", "value": round(22.0 + i * 0.1, 1)}) for i in range(1, 9)]


def sse(event_id, data, event="reading"):
    return f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream(last_event_id=None, min_delta=0.25):
    """從 last_event_id 之後送出；數值變化小於 min_delta 的略過，降低前端重繪。"""
    last_sent = None
    for eid, data in EVENTS:
        if last_event_id is not None and eid <= last_event_id:
            continue
        if last_sent is not None and abs(data["value"] - last_sent) < min_delta:
            continue
        last_sent = data["value"]
        yield sse(eid, data)
    yield "retry: 5000\n\n"                   # 告訴瀏覽器斷線後 5 秒重連


if __name__ == "__main__":
    print("== 首次連線")
    print("".join(stream()), end="")
    print("== 斷線後重連，Last-Event-ID: 5")
    print("".join(stream(last_event_id=5)), end="")
