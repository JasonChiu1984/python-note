"""Local, synthetic FastAPI connection lab. Run with:

    python -m uvicorn python_frontend_dataflow_connection_lab:app --host 127.0.0.1 --port 8000

This lab requires fastapi and uvicorn; WebSocket needs a supported ASGI backend
such as websockets (installed with uvicorn[standard]). No production auth or replay.
"""
import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI()

DEMO_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>資料流連接實驗</title>
<h1>離線合成資料：Fetch、SSE、WebSocket</h1>
<button id="fetch">讀快照</button>
<button id="sse">啟動 SSE</button>
<button id="ws">啟動 WebSocket</button>
<button id="stop">中止串流</button>
<pre id="output" aria-live="polite"></pre>
<script>
const byId = id => document.getElementById(id);
let stream, socket;
function show(record) { byId("output").textContent = JSON.stringify(record, null, 2); }
function stop() {
  stream?.close();
  socket?.close();
  stream = socket = undefined;
}
byId("stop").onclick = stop;
byId("fetch").onclick = async () => {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 2000);
  try {
    const res = await fetch("/api/snapshot", {signal: ctl.signal});
    if (!res.ok) throw new Error("HTTP " + res.status);
    show(await res.json());
  } catch (e) {
    show({error: e.name, message: e.message});
  } finally { clearTimeout(timer); }
};
byId("sse").onclick = () => {
  stop();
  stream = new EventSource("/api/events");
  stream.addEventListener("reading", e => {
    show(JSON.parse(e.data));
    if (e.lastEventId === "3") stream?.close();
  });
  stream.onerror = () => { show({error: "SSE disconnected"}); stop(); };
};
byId("ws").onclick = () => {
  stop();
  const url = new URL("/api/ws", location.href);
  url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(url);
  socket.onopen = () => socket.send("snapshot");
  socket.onmessage = e => {
    show(JSON.parse(e.data));
    socket?.close();
  };
  socket.onerror = () => show({error:"WebSocket error"});
};
addEventListener("pagehide", stop);
</script>"""


def envelope(seq, transport):
    return {"schema_version": 1, "seq": seq, "transport": transport,
            "sensor_id": "T10", "value_c": 24.0 + seq / 10, "quality": "good"}


@app.get("/", response_class=HTMLResponse)
def page():
    return DEMO_PAGE


@app.get("/api/snapshot")
def snapshot():
    return envelope(0, "fetch")


@app.get("/api/events")
async def events():
    async def generate():
        for seq in range(1, 4):
            payload = json.dumps(envelope(seq, "sse"), ensure_ascii=False)
            yield f"id: {seq}\nevent: reading\ndata: {payload}\n\n"
            await asyncio.sleep(0.15)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.websocket("/api/ws")
async def socket(ws: WebSocket):
    # Fixed allowlist for this loopback demonstration. Not an auth mechanism.
    if ws.headers.get("origin") not in ("http://127.0.0.1:8000", "http://localhost:8000"):
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        command = await asyncio.wait_for(ws.receive_text(), timeout=3)
        if command != "snapshot":
            await ws.close(code=1008)
            return
        await ws.send_json(envelope(1, "websocket"))
        await ws.close()
    except asyncio.TimeoutError:
        await ws.close(code=1008)
    except WebSocketDisconnect:
        pass
