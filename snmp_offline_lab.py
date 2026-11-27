"""Synthetic IF-MIB analytics. No network, credentials or packet construction."""
from dataclasses import dataclass
import math
import unittest


@dataclass(frozen=True)
class Sample:
    # Collector monotonic timestamp; all samples must share the same clock.
    t_s: float
    agent: str
    if_index: int
    octets: int
    # Collector-assigned continuity epoch; changes on known restart/remapping.
    epoch: int
    # Equivalent to a collected ifCounterDiscontinuityTime value.
    discontinuity: int


@dataclass(frozen=True)
class Rate:
    quality: str
    bps: float | None = None
    utilization_pct: float | None = None


def evaluate(a: Sample, b: Sample, *, width: int, capacity_bps: int,
             max_gap_s: float = 90.0) -> Rate:
    """Return an explicit quality state rather than treating gaps as zero."""
    if width not in (32, 64) or type(capacity_bps) is not int or capacity_bps <= 0:
        raise ValueError("invalid counter width or capacity")
    if not math.isfinite(max_gap_s) or max_gap_s <= 0:
        raise ValueError("invalid gap limit")
    modulus = 1 << width
    if any(type(x.octets) is not int or not 0 <= x.octets < modulus
           or type(x.if_index) is not int or x.if_index <= 0
           or not x.agent or not math.isfinite(x.t_s) for x in (a, b)):
        return Rate("invalid-sample")
    if (a.agent, a.if_index) != (b.agent, b.if_index):
        return Rate("different-series")
    dt = b.t_s - a.t_s
    if not math.isfinite(dt) or dt <= 0:
        return Rate("time-order")
    if dt > max_gap_s:
        return Rate("stale-gap")
    if a.epoch != b.epoch or a.discontinuity != b.discontinuity:
        return Rate("discontinuity")
    max_octets = capacity_bps * dt / 8
    delta = (b.octets - a.octets) % modulus
    if delta > max_octets:
        return Rate("capacity-exceeded")
    if delta + modulus <= max_octets:
        return Rate("ambiguous-wrap")
    bps = 8 * delta / dt
    return Rate("ok", bps, 100 * bps / capacity_bps)


class Cases(unittest.TestCase):
    def test_good(self):
        a = Sample(0, "synthetic-a", 7, 100_000, 1, 0)
        b = Sample(15, "synthetic-a", 7, 125_100_000, 1, 0)
        x = evaluate(a, b, width=64, capacity_bps=1_000_000_000)
        self.assertEqual(x.quality, "ok")
        self.assertAlmostEqual(x.bps, 66_666_666.666667, places=5)
        self.assertAlmostEqual(x.utilization_pct, 6.666666666666667)

    def test_single_wrap(self):
        x = evaluate(Sample(0, "a", 1, (1 << 32) - 16, 1, 0),
                     Sample(1, "a", 1, 16, 1, 0),
                     width=32, capacity_bps=100_000_000)
        self.assertEqual(x, Rate("ok", 256.0, 0.000256))

    def test_multiple_compatible_deltas(self):
        a = Sample(0, "a", 1, 10, 1, 0)
        b = Sample(60, "a", 1, 20, 1, 0)
        self.assertEqual(evaluate(a, b, width=32, capacity_bps=1_000_000_000),
                         Rate("ambiguous-wrap"))

    def test_gap_and_restart(self):
        a = Sample(0, "a", 1, 100, 1, 0)
        for b, quality in [(Sample(91, "a", 1, 200, 1, 0), "stale-gap"),
                           (Sample(1, "a", 1, 10, 2, 0), "discontinuity"),
                           (Sample(1, "a", 1, 10, 1, 5), "discontinuity")]:
            self.assertEqual(evaluate(a, b, width=64, capacity_bps=1_000_000_000),
                             Rate(quality))

    def test_bad_samples(self):
        a = Sample(1, "a", 1, 10, 1, 0)
        for b, quality in [(Sample(1, "a", 1, 20, 1, 0), "time-order"),
                           (Sample(2, "b", 1, 20, 1, 0), "different-series"),
                           (Sample(2, "a", 1, -1, 1, 0), "invalid-sample"),
                           (Sample(2, "a", 1, 4_000_000_000, 1, 0), "capacity-exceeded")]:
            self.assertEqual(evaluate(a, b, width=32, capacity_bps=1_000_000_000),
                             Rate(quality))


if __name__ == "__main__":
    unittest.main(verbosity=2)
