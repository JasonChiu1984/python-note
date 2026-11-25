"""Offline discrete-event lab. No network, device, background timing or I/O."""
import argparse
from collections import deque
from dataclasses import dataclass
import json
import math
import unittest


@dataclass(frozen=True)
class Poll:
    arrival_ms: int
    station: int


def nearest_rank(values, fraction):
    """Return the nearest-rank percentile (no interpolation)."""
    if not values or not 0 < fraction <= 1:
        raise ValueError("need samples and a quantile in (0, 1]")
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def simulate(slow=False, retry=0, limit=24, rounds=12):
    """One FIFO RTU port; limit includes the in-flight request."""
    if retry not in (0, 1) or limit < 1 or rounds < 1:
        raise ValueError("invalid offline scenario")
    outstanding_finishes = deque()
    next_free = 0
    traces = []
    dropped = 0
    for cycle in range(rounds):
        for station in range(1, 21):
            # Identical offered timestamps in every scenario. Integer ms is model time.
            poll = Poll(cycle * 500 + (station - 1) * 5, station)
            while outstanding_finishes and outstanding_finishes[0] <= poll.arrival_ms:
                outstanding_finishes.popleft()
            if len(outstanding_finishes) >= limit:
                dropped += 1
                continue
            start = max(next_free, poll.arrival_ms)
            timed_out = slow and poll.station == 1
            service = 300 * (1 + retry) if timed_out else 20
            finish = start + service
            next_free = finish
            outstanding_finishes.append(finish)
            traces.append({
                "station": poll.station,
                "arrive_ms": poll.arrival_ms,
                "queue_ms": start - poll.arrival_ms,
                "service_ms": service,
                "delay_ms": finish - poll.arrival_ms,
                "timeout": timed_out,
            })
    successful = [row for row in traces if not row["timeout"]]
    latency = [row["delay_ms"] for row in successful]
    return {
        "offered": 20 * rounds,
        "completed_ok": len(successful),
        "timeout": sum(row["timeout"] for row in traces),
        "queue_rejected": dropped,
        "p95_success_ms": nearest_rank(latency, .95) if latency else None,
        "p99_success_ms": nearest_rank(latency, .99) if latency else None,
        "max_healthy_queue_ms": max((x["queue_ms"] for x in successful), default=None),
    }


class LabTests(unittest.TestCase):
    def test_nearest_rank(self):
        self.assertEqual(nearest_rank([30, 10, 20], .95), 30)
        self.assertEqual(nearest_rank([30, 10, 20], .50), 20)
        with self.assertRaises(ValueError):
            nearest_rank([], .99)

    def test_station_failure_hurts_other_stations(self):
        baseline = simulate()
        slow = simulate(slow=True)
        self.assertEqual(baseline["completed_ok"], 240)
        self.assertEqual(baseline["queue_rejected"], 0)
        self.assertEqual(baseline["timeout"], 0)
        self.assertGreater(slow["p95_success_ms"], baseline["p95_success_ms"])
        self.assertGreater(slow["timeout"], 0)

    def test_more_service_cost(self):
        self.assertGreater(simulate(slow=True, retry=1)["max_healthy_queue_ms"],
                           simulate(slow=True)["max_healthy_queue_ms"])

    def test_balanced_accounting(self):
        for slow, retry in [(False, 0), (True, 0), (True, 1)]:
            x = simulate(slow=slow, retry=retry)
            self.assertEqual(x["offered"], x["completed_ok"] + x["timeout"] + x["queue_rejected"])

    def test_bound(self):
        self.assertGreater(simulate(slow=True, limit=1)["queue_rejected"], 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=["lab"], verbosity=2)
    else:
        print(json.dumps({
            "healthy": simulate(),
            "slow_station": simulate(slow=True),
            "slow_station_retry": simulate(slow=True, retry=1),
        }, indent=2))


if __name__ == "__main__":
    main()
