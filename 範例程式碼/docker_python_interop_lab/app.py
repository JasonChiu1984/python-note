"""唯讀合成遙測；不與現場設備通訊。"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SAMPLE = {"schema": 1, "point": "supply_temp", "value": 7.2, "unit": "degC", "quality": "synthetic"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code, payload = {
            "/healthz": (200, {"status": "ok"}),
            "/sample": (200, SAMPLE),
        }.get(self.path, (404, {"error": "not_found"}))
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    if sys.argv[1:] == ["sample"]:
        print(json.dumps(SAMPLE))
        return
    if sys.argv[1:]:
        raise SystemExit("usage: python app.py [sample]")
    # 此實驗只示範資料交換；正式訊號與收尾見原部署教材。
    with ThreadingHTTPServer(("0.0.0.0", 8080), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
