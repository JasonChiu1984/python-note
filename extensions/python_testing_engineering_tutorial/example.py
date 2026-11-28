"""用 unittest 測試設備邏輯：以假時鐘與假通訊取代真實設備，涵蓋正常、逾時與邊界（標準函式庫）。"""
import io
import unittest


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def advance(self, s):
        self.t += s


class FakeModbus:
    def __init__(self, values):
        self.values, self.calls = list(values), 0

    def read(self):
        self.calls += 1
        v = self.values.pop(0)
        if isinstance(v, Exception):
            raise v
        return v


class HighTempAlarm:
    """連續高於門檻達 delay 秒才告警；通訊失敗時回報 'comm_fail'，不誤報高溫。"""

    def __init__(self, dev, clock, limit=28.0, delay=60):
        self.dev, self.clock, self.limit, self.delay, self.since = dev, clock, limit, delay, None

    def poll(self):
        try:
            v = self.dev.read()
        except TimeoutError:
            self.since = None
            return "comm_fail"
        if v <= self.limit:
            self.since = None
            return "normal"
        self.since = self.since if self.since is not None else self.clock.now()
        return "alarm" if self.clock.now() - self.since >= self.delay else "pending"


class TestHighTempAlarm(unittest.TestCase):
    def run_sequence(self, values, step=30):
        clock, dev = FakeClock(), FakeModbus(values)
        a = HighTempAlarm(dev, clock)
        out = []
        for _ in values:
            out.append(a.poll())
            clock.advance(step)
        return out

    def test_alarm_after_delay(self):
        self.assertEqual(self.run_sequence([29, 29, 29]), ["pending", "pending", "alarm"])

    def test_short_spike_no_alarm(self):
        self.assertEqual(self.run_sequence([29, 27, 29]), ["pending", "normal", "pending"])

    def test_exactly_at_limit_is_normal(self):
        self.assertEqual(self.run_sequence([28.0]), ["normal"])

    def test_timeout_resets_and_is_not_alarm(self):
        self.assertEqual(self.run_sequence([29, TimeoutError(), 29, 29]),
                         ["pending", "comm_fail", "pending", "pending"])


if __name__ == "__main__":
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestHighTempAlarm))
    for line in stream.getvalue().splitlines():
        if line.endswith(("ok", "FAIL", "ERROR")):
            print(line.split(" (")[0], "→", line.rsplit(" ", 1)[-1])
    print(f"共 {result.testsRun} 個測試，失敗 {len(result.failures)}，錯誤 {len(result.errors)}")
