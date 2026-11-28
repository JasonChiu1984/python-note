"""斷路器：連續失敗後暫停呼叫外部系統，冷卻後試探一次，成功才恢復（標準函式庫，使用模擬時鐘）。"""


class CircuitBreaker:
    def __init__(self, threshold=3, cooldown=30.0, clock=None):
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.state, self.failures, self.opened_at = "closed", 0, None

    def call(self, fn):
        now = self.clock()
        if self.state == "open":
            if now - self.opened_at < self.cooldown:
                return "略過（斷路中）"
            self.state = "half_open"
        try:
            result = fn()
        except Exception as e:
            self.failures += 1
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self.opened_at = "open", now
            return f"失敗：{e}"
        self.state, self.failures = "closed", 0
        return f"成功：{result}"


if __name__ == "__main__":
    t = [0.0]
    up = {"ok": False}

    def energy_api():
        if not up["ok"]:
            raise ConnectionError("能源平台無回應")
        return "上傳 120 筆"

    cb = CircuitBreaker(clock=lambda: t[0])
    timeline = [(0, False), (5, False), (10, False), (15, False), (25, False),
                (41, False), (75, True), (80, True)]
    for at, ok in timeline:
        t[0], up["ok"] = at, ok
        before = cb.state
        print(f"t={at:>3}s 狀態 {before:<9} → {cb.call(energy_api):<16} 之後 {cb.state}")
