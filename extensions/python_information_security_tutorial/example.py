"""閘道器輸入驗證：白名單點位、數值範圍、速率變化與重放檢查（標準函式庫）。

情境：MQTT 或 HTTP 收到的溫度事件，在寫入資料庫或轉給控制系統前要先驗證。
"""
import hashlib
import hmac
import json
import time

ALLOWED = {"AHU1_SAT": (5.0, 40.0, 2.0), "CHW_SUPPLY": (3.0, 15.0, 1.0)}   # 下限、上限、每分鐘最大變化
KEY = b"\x07" * 32
NOW = 1_795_800_000                                       # 固定「現在」時間，讓輸出可重現


class Validator:
    def __init__(self):
        self.last: dict[str, tuple[int, float]] = {}
        self.seen_nonce: set[str] = set()

    def check(self, raw: bytes) -> str:
        if len(raw) > 512:
            return "拒絕：訊息過大"
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return "拒絕：不是合法 JSON"
        body = {k: msg.get(k) for k in ("point", "value", "ts", "nonce")}
        sig = hmac.new(KEY, json.dumps(body, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, str(msg.get("sig", ""))):
            return "拒絕：簽章錯誤"
        if not isinstance(body["point"], str) or body["point"] not in ALLOWED:   # list 等不可雜湊型別也拒絕，不讓 in 拋 TypeError
            return f"拒絕：未知點位 {body['point']!r}"
        if not isinstance(body["value"], (int, float)) or isinstance(body["value"], bool):
            return "拒絕：數值型別錯誤"
        if type(body["ts"]) is not int or not isinstance(body["nonce"], str):
            return "拒絕：時間戳或 nonce 型別錯誤"
        if abs(NOW - body["ts"]) > 300:
            return "拒絕：時間戳超出 ±5 分鐘"
        if body["nonce"] in self.seen_nonce:
            return "拒絕：重放（nonce 已使用）"
        lo, hi, rate = ALLOWED[body["point"]]
        if not lo <= body["value"] <= hi:
            return f"隔離：{body['value']} 超出 {lo}–{hi}"
        prev = self.last.get(body["point"])
        if prev and abs(body["value"] - prev[1]) > rate * max(1, (body["ts"] - prev[0]) / 60):
            return f"隔離：變化過快（{prev[1]} → {body['value']}）"
        self.seen_nonce.add(body["nonce"])
        self.last[body["point"]] = (body["ts"], body["value"])
        return "接受"


def make(point, value, ts, nonce, key=KEY):
    body = {"point": point, "value": value, "ts": ts, "nonce": nonce}
    body["sig"] = hmac.new(key, json.dumps(body, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    return json.dumps(body).encode()


if __name__ == "__main__":
    v = Validator()
    cases = [
        ("正常", make("AHU1_SAT", 18.2, NOW - 60, "a1")),
        ("重放同一封包", make("AHU1_SAT", 18.2, NOW - 60, "a1")),
        ("跳變", make("AHU1_SAT", 26.0, NOW, "a2")),
        ("未知點位", make("AHU9_SAT", 18.0, NOW, "a3")),
        ("超出範圍", make("CHW_SUPPLY", 55.0, NOW, "a4")),
        ("過期", make("CHW_SUPPLY", 7.0, NOW - 3600, "a5")),
        ("偽造簽章", make("CHW_SUPPLY", 7.0, NOW, "a6", key=b"x" * 32)),
        ("型別錯誤", make("CHW_SUPPLY", "7.0", NOW, "a7")),
        ("非 JSON", b"<xml/>"),
    ]
    for name, raw in cases:
        print(f"{name:<8} → {v.check(raw)}")
