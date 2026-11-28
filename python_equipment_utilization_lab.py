"""合成運轉回授範例。時間以同一時間基準的整數分鐘表示，不連設備。"""
from dataclasses import dataclass
from fractions import Fraction
import json
import unittest
from bisect import bisect_right


@dataclass(frozen=True)
class Event:
    minute: int
    running: bool | None

    def __post_init__(self):
        if self.running is not True and self.running is not False and self.running is not None:
            raise TypeError("運轉回授必須是 True、False 或 None；請先解碼原始點位")


def merge_schedule(spans, start, end):
    """先裁切再取聯集，避免重疊排程重複計時。"""
    selected = []
    for left, right in spans:
        if left >= right:
            raise ValueError("排程區間須有正長度")
        lo, hi = max(left, start), min(right, end)
        if lo < hi:
            selected.append((lo, hi))
    out = []
    for lo, hi in sorted(selected):
        if out and lo <= out[-1][1]:
            out[-1] = (out[-1][0], max(hi, out[-1][1]))
        else:
            out.append((lo, hi))
    return out


def utilization(events, schedule, start, end, ttl):
    """回授適用 [event, event+ttl)；None 是立即失效，不是停機。"""
    if not start < end or ttl <= 0:
        raise ValueError("須有正長度觀測窗與正數時效")
    samples = {}
    for event in events:
        if event.minute >= end:
            continue  # 位於右端點的事件屬於下一窗
        if event.minute in samples and samples[event.minute] is not event.running:
            raise ValueError("同時戳回授衝突，須先由來源裁決")
        samples[event.minute] = event.running
    times = sorted(samples)
    spans = merge_schedule(schedule, start, end)
    cuts = {start, end}
    cuts.update(t for lo, hi in spans for t in (lo, hi))
    cuts.update(t for event_t in times for t in (event_t, event_t + ttl)
                if start < t < end)
    timeslices = sorted(cuts)
    sums = {scope: {"run": 0, "stop": 0, "unknown": 0}
            for scope in ("calendar", "schedule")}
    trace = []
    for left, right in zip(timeslices, timeslices[1:]):
        idx = bisect_right(times, left) - 1
        state = (samples[times[idx]]
                 if idx >= 0 and left < times[idx] + ttl else None)
        status = "run" if state is True else "stop" if state is False else "unknown"
        planned = any(lo <= left < hi for lo, hi in spans)
        sums["calendar"][status] += right - left
        if planned:
            sums["schedule"][status] += right - left
        trace.append({"start": left, "end": right, "status": status, "planned": planned})
    return sums, trace


def fractions(time):
    run, stop, unknown = (time[key] for key in ("run", "stop", "unknown"))
    total, known = run + stop + unknown, run + stop
    return {
        "coverage": Fraction(known, total) if total else None,
        "known_only": Fraction(run, known) if known else None,
        "lower": Fraction(run, total) if total else None,
        "upper": Fraction(run + unknown, total) if total else None,
    }


FIXTURE = (
    Event(-5, True), Event(10, True), Event(10, True), Event(20, False),
    Event(37, None), Event(45, True), Event(60, False)
)
SCHEDULE = [(5, 25), (20, 50)]


class LabTests(unittest.TestCase):
    def test_reject_raw_point_values(self):
        for raw in (0, 1, "0", "1", 1.0, [], object()):
            with self.subTest(raw=raw), self.assertRaises(TypeError):
                Event(0, raw)

    def test_decoded_bit_yields_complete_coverage(self):
        sums, _ = utilization([Event(0, True), Event(5, False)], [(0, 10)], 0, 10, 10)
        self.assertEqual(sums["schedule"], {"run": 5, "stop": 5, "unknown": 0})
        self.assertEqual(fractions(sums["schedule"])["coverage"], Fraction(1))

    def test_aggregate_and_half_open(self):
        sums, trace = utilization(FIXTURE, SCHEDULE, 0, 60, 15)
        self.assertEqual(sums["calendar"], {"run": 35, "stop": 15, "unknown": 10})
        self.assertEqual(sums["schedule"], {"run": 20, "stop": 15, "unknown": 10})
        self.assertEqual(fractions(sums["schedule"])["upper"], Fraction(2, 3))
        self.assertEqual(trace[-1]["status"], "run")

    def test_stale_and_quality_edge(self):
        sums, trace = utilization([Event(-10, True), Event(2, True), Event(3, None),
                                   Event(5, False)], [], 0, 10, 3)
        self.assertEqual(sums["calendar"], {"run": 1, "stop": 3, "unknown": 6})
        self.assertIsNone(fractions(sums["schedule"])["coverage"])

    def test_conflicting_duplicates(self):
        with self.assertRaises(ValueError):
            utilization([Event(1, True), Event(1, False)], [], 0, 4, 3)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        unittest.main(argv=["lab"])
    else:
        counts, trace = utilization(FIXTURE, SCHEDULE, 0, 60, 15)
        result = {scope: dict(minutes=value, fractions=fractions(value))
                  for scope, value in counts.items()}
        print(json.dumps(dict(result=result, trace=trace), default=str,
                         ensure_ascii=False, indent=2))
