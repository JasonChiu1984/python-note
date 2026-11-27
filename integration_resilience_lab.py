"""整合韌性教材：確定性模擬，沒有網路 I/O。"""
from dataclasses import dataclass
import json
from urllib.parse import urlencode
import unittest


class ApiFailure(Exception):
    """所有策略失敗，都有明確原因。"""


class Breaker:
    """同步單用戶範例：連續兩次可用性失敗開路；冷卻後試探。"""
    def __init__(self, threshold=2, cool_ms=100):
        self.threshold = threshold
        self.cool_ms = cool_ms
        self.failures = 0
        self.until = None
        self.state = "closed"

    def permit(self, now):
        if self.state == "half_open":
            raise ApiFailure("probe_in_progress")
        if self.until is not None:
            if now < self.until:
                raise ApiFailure("circuit_open")
            self.state = "half_open"

    def success(self):
        self.failures = 0
        self.until = None
        self.state = "closed"

    def failure(self, now):
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.threshold:
            self.until = now + self.cool_ms
            self.state = "open"


@dataclass(frozen=True)
class Reply:
    status: int
    elapsed_ms: int
    body: object = None
    retry_after: str | None = None  # 教學僅接受 HTTP delay-seconds。


class FakeTransport:
    """虛擬時鐘：模型會遵守本次 timeout 上限。"""
    def __init__(self, replies):
        self.replies = iter(replies)
        self.now = 0
        self.calls = []

    def sleep_ms(self, delay):
        self.now += delay

    def request(self, method, path, timeout_ms):
        self.calls.append((method, path, timeout_ms))
        reply = next(self.replies)
        self.sleep_ms(min(reply.elapsed_ms, timeout_ms))
        if reply.elapsed_ms > timeout_ms:
            raise TimeoutError()
        return reply


def request(transport, breaker, method, path, total_ms=240, attempts=3):
    if total_ms <= 0 or attempts <= 0:
        raise ValueError("預算和嘗試次數必須為正")
    deadline = transport.now + total_ms
    reason = "unknown"
    for attempt in range(attempts):
        remaining = deadline - transport.now
        if remaining <= 0:
            raise ApiFailure("deadline")
        breaker.permit(transport.now)
        retry_after = None
        try:
            reply = transport.request(method, path, min(80, remaining))
        except TimeoutError:
            reason = "timeout"
            breaker.failure(transport.now)
        else:
            status = reply.status
            if status == 200:
                breaker.success()
                return reply.body
            reason = f"http_{status}"
            if status in (502, 503, 504):
                breaker.failure(transport.now)
                if status == 503:
                    retry_after = reply.retry_after
            elif status == 429:
                if breaker.state == "half_open":
                    breaker.failure(transport.now)
                retry_after = reply.retry_after
            else:
                # 可連線但非預期業務回應，不列為此 demo 的可用性故障。
                breaker.success()
                raise ApiFailure(reason)

        if transport.now >= deadline:
            raise ApiFailure("deadline")
        # 本例僅自動重試 GET；寫入要另有服務端契約。
        if method != "GET" or attempt + 1 == attempts:
            raise ApiFailure(reason)
        if breaker.state == "open":
            raise ApiFailure("circuit_open")
        # 確定性測試固定退避；正式版加入 jitter。服務端等待是下限而非取代退避。
        delay = min(200, 25 * 2 ** min(attempt, 4))
        if retry_after is not None:
            # 只接受最多 9 位 ASCII 數字；日期格式保守交回上層。
            if not (
                1 <= len(retry_after) <= 9
                and retry_after.isascii()
                and retry_after.isdecimal()
            ):
                raise ApiFailure("retry_after_unsupported")
            delay = max(delay, int(retry_after) * 1000)
        if delay >= deadline - transport.now:
            raise ApiFailure("deadline")
        transport.sleep_ms(delay)
    raise AssertionError("unreachable")


def parse_page(body):
    if type(body) is not dict or type(body.get("items")) is not list:
        raise ApiFailure("schema")
    ids = []
    for row in body["items"]:
        if type(row) is not dict or type(row.get("id")) is not int:
            raise ApiFailure("schema")
        ids.append(row["id"])
    cursor = body.get("next")
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        raise ApiFailure("schema")
    return ids, cursor


def poll_pages(transport, breaker, max_pages=4, total_ms=400):
    seen = set()
    ids = []
    cursor = None
    deadline = transport.now + total_ms
    for _ in range(max_pages):
        path = "/items" + (("?" + urlencode({"cursor": cursor})) if cursor else "")
        left = deadline - transport.now
        if left <= 0:
            raise ApiFailure("poll_deadline")
        items, cursor = parse_page(
            request(transport, breaker, "GET", path, total_ms=min(left, 240))
        )
        ids.extend(items)
        if cursor is None:
            return ids
        if cursor in seen:
            raise ApiFailure("cursor_loop")
        seen.add(cursor)
    raise ApiFailure("page_cap")


class Tests(unittest.TestCase):
    def test_transient_recovery(self):
        t = FakeTransport([Reply(503, 40), Reply(200, 55, {"ok": True})])
        self.assertTrue(request(t, Breaker(), "GET", "/items")["ok"])
        self.assertEqual((len(t.calls), t.now), (2, 120))

    def test_throttle_budget(self):
        t = FakeTransport([Reply(429, 20, retry_after="1")])
        with self.assertRaisesRegex(ApiFailure, "deadline"):
            request(t, Breaker(), "GET", "/items")
        self.assertEqual((len(t.calls), t.now), (1, 20))

    def test_unavailable_retry_after_budget(self):
        for budget in (240, 1020):
            with self.subTest(budget=budget):
                t = FakeTransport([Reply(503, 20, retry_after="1"), Reply(200, 10, {})])
                with self.assertRaisesRegex(ApiFailure, "deadline"):
                    request(t, Breaker(), "GET", "/items", total_ms=budget)
                self.assertEqual((len(t.calls), t.now), (1, 20))

        t = FakeTransport([Reply(503, 20, retry_after="1"), Reply(200, 10, {"ok": True})])
        self.assertTrue(request(t, Breaker(), "GET", "/items", total_ms=1035)["ok"])
        # 首次回應在 20 ms；等待 1000 ms 才重試，所以第二次 timeout 只剩 15 ms。
        self.assertEqual(([call[2] for call in t.calls], t.now), ([80, 15], 1030))

    def test_server_zero_wait_keeps_local_backoff(self):
        for status in (429, 503):
            with self.subTest(status=status):
                t = FakeTransport([Reply(status, 20, retry_after="0"), Reply(200, 10, {})])
                self.assertEqual(request(t, Breaker(), "GET", "/items"), {})
                self.assertEqual((len(t.calls), t.now), (2, 55))

    def test_budget_includes_attempts_and_backoff(self):
        t = FakeTransport([Reply(200, 100), Reply(200, 100)])
        with self.assertRaisesRegex(ApiFailure, "deadline"):
            request(t, Breaker(), "GET", "/items", total_ms=120)
        self.assertEqual((t.now, [call[2] for call in t.calls]), (120, [80, 15]))

    def test_never_retry_post(self):
        t = FakeTransport([Reply(503, 40)])
        with self.assertRaisesRegex(ApiFailure, "http_503"):
            request(t, Breaker(), "POST", "/orders")
        self.assertEqual(len(t.calls), 1)

    def test_breaker(self):
        t = FakeTransport([Reply(503, 40), Reply(503, 30), Reply(200, 20, {})])
        b = Breaker()
        with self.assertRaisesRegex(ApiFailure, "circuit_open"):
            request(t, b, "GET", "/items")
        with self.assertRaisesRegex(ApiFailure, "circuit_open"):
            request(t, b, "GET", "/items")
        self.assertEqual(len(t.calls), 2)
        t.sleep_ms(100)
        request(t, b, "GET", "/items")
        self.assertEqual((b.state, len(t.calls)), ("closed", 3))

    def test_schema(self):
        with self.assertRaisesRegex(ApiFailure, "schema"):
            parse_page({"items": [{"id": True}]})

    def test_pagination(self):
        t = FakeTransport([
            Reply(200, 10, {"items": [{"id": 1}], "next": "abc+/="}),
            Reply(200, 12, {"items": [{"id": 2}]}),
        ])
        self.assertEqual(poll_pages(t, Breaker()), [1, 2])
        self.assertEqual(t.calls[1][1], "/items?cursor=abc%2B%2F%3D")

    def test_cursor_loop(self):
        page = {"items": [{"id": 1}], "next": "repeated"}
        t = FakeTransport([Reply(200, 10, page), Reply(200, 10, page)])
        with self.assertRaisesRegex(ApiFailure, "cursor_loop"):
            poll_pages(t, Breaker())

    def test_401_is_not_retried(self):
        t = FakeTransport([Reply(401, 25)])
        with self.assertRaisesRegex(ApiFailure, "http_401"):
            request(t, Breaker(), "GET", "/items")
        self.assertEqual((len(t.calls), t.now), (1, 25))


if __name__ == "__main__":
    demo = FakeTransport([Reply(503, 40), Reply(200, 55, {"ok": True})])
    payload = request(demo, Breaker(), "GET", "/items")
    print(json.dumps({"synthetic_ms": demo.now, "requests": len(demo.calls),
                      "payload": payload}, ensure_ascii=False), flush=True)
    unittest.main(verbosity=2)
