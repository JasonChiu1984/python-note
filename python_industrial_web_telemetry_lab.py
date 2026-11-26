"""工業遙測游標實驗。只操作合成資料；不是 WebSocket 或 REST 伺服器。"""
from dataclasses import dataclass
import argparse
import unittest


class Gap(ValueError):
    """應用層串流有缺口。"""


class ResyncRequired(ValueError):
    """游標已超過本資料集的保留範圍。"""


@dataclass(frozen=True)
class Event:
    stream: str
    seq: int
    value: float | None
    quality: str


@dataclass
class Subscriber:
    stream: str
    last_seq: int

    def apply(self, event: Event) -> bool:
        if event.stream != self.stream:
            raise ValueError("事件不屬於此訂閱")
        if event.seq <= self.last_seq:
            return False
        if event.seq != self.last_seq + 1:
            raise Gap(f"期待 seq={self.last_seq + 1}，收到 seq={event.seq}")
        self.last_seq = event.seq
        return True


def replay(history: tuple[Event, ...], stream: str, after_seq: int) -> tuple[Event, ...]:
    """合成資料已按 seq 排序，且只截去最舊事件；不是跨連線原子快照。"""
    rows = tuple(e for e in history if e.stream == stream)
    if not rows:
        if after_seq != 0:
            raise ResyncRequired("未找到串流保留範圍")
        return ()
    if after_seq < rows[0].seq - 1 or after_seq > rows[-1].seq:
        raise ResyncRequired("需要重新取得快照")
    return tuple(e for e in rows if e.seq > after_seq)


HISTORY = (Event("ahu-01", 43, 24.3, "GOOD"),
           Event("ahu-01", 44, None, "STALE"))


class Tests(unittest.TestCase):
    def test_order_and_duplicate(self):
        s = Subscriber("ahu-01", 42)
        self.assertTrue(s.apply(HISTORY[0]))
        self.assertFalse(s.apply(HISTORY[0]))
        self.assertTrue(s.apply(HISTORY[1]))
        self.assertEqual(s.last_seq, 44)
        self.assertIsNone(HISTORY[1].value)

    def test_gap_does_not_advance_then_replays(self):
        s = Subscriber("ahu-01", 42)
        with self.assertRaises(Gap):
            s.apply(HISTORY[1])
        self.assertEqual(s.last_seq, 42)
        self.assertEqual([e.seq for e in replay(HISTORY, s.stream, s.last_seq)], [43, 44])

    def test_expired_future_cursor(self):
        for cursor in (41, 45):
            with self.subTest(cursor=cursor), self.assertRaises(ResyncRequired):
                replay(HISTORY, "ahu-01", cursor)

    def test_other_stream(self):
        s = Subscriber("ahu-01", 42)
        with self.assertRaises(ValueError):
            s.apply(Event("ahu-02", 43, 24.5, "GOOD"))
        self.assertEqual(s.last_seq, 42)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true")
    if p.parse_args().test:
        tests = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(tests).wasSuccessful() else 1
    subscriber = Subscriber("ahu-01", 42)
    try:
        subscriber.apply(HISTORY[1])
    except Gap as error:
        print(error)
    for e in replay(HISTORY, subscriber.stream, subscriber.last_seq):
        if subscriber.apply(e):
            print(e.seq, e.quality, e.value)
    print("last_seq =", subscriber.last_seq)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
