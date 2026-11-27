"""Offline NumPy experiments. Synthetic inputs only; no device or network I/O."""
import argparse
import json
import math
from statistics import median
from time import perf_counter_ns
import unittest

import numpy as np


def memory_contract():
    a = np.arange(12, dtype=np.int32).reshape(3, 4)
    view = a[:, ::-2]
    copied = a[:, [3, 1]]
    view[0, 0] = 99
    assert copied[0, 0] == 3 and a[0, 3] == 99
    return {"shape": list(view.shape), "strides_bytes": list(view.strides),
            "view_aliases": bool(np.shares_memory(a, view)),
            "advanced_index_aliases": bool(np.shares_memory(a, copied))}


def telemetry_contract(raw, reference):
    # Axes: physical channel identity needs upstream schema validation too.
    x, ref = np.asarray(raw, dtype=np.float64), np.asarray(reference, dtype=np.float64)
    if x.ndim != 2 or ref.shape != (x.shape[1],) or x.shape[1] == 0:
        raise ValueError("expected x=(time, channel), ref=(channel,)")
    valid = np.isfinite(x) & np.isfinite(ref) & (ref > 0)
    out = np.full(x.shape, np.nan)
    np.divide(x, ref, out=out, where=valid)
    return out, np.count_nonzero(valid, axis=0)


def accumulator_contract():
    raw = np.array([30_000], dtype=np.int16)
    offset = np.array([10_000], dtype=np.int16)
    bad = int((raw + offset)[0])
    safe = int(np.add(raw, offset, dtype=np.int32)[0])
    cancellation = [1e16, 1.0, -1e16]
    return {"narrow": bad, "wide": safe, "ordinary_sum": float(np.sum(cancellation)),
            "fsum_reference": math.fsum(cancellation)}


def calibration_contract():
    # Model: synthetic temperature output = gain * reference + offset.
    ref = np.array([0., 10., 20., 30.])
    y = 1.05 * ref + 2.0
    design = np.column_stack((ref, np.ones_like(ref)))
    coeff, _, rank, spectrum = np.linalg.lstsq(design, y, rcond=None)
    if rank != design.shape[1]:
        raise ValueError("gain and offset not identifiable")
    error = np.linalg.norm(design @ coeff - y)
    return {"gain": float(coeff[0]), "offset": float(coeff[1]), "rank": int(rank),
            "residual_l2_degC": float(error),
            "condition_2": float(spectrum[0] / spectrum[-1])}


def energy_contract(flow_l_s, delta_k, second_edges, valid):
    q, dt = np.asarray(flow_l_s, dtype=np.float64), np.asarray(delta_k, dtype=np.float64)
    edges = np.asarray(second_edges, dtype=np.float64)
    mask = np.asarray(valid)
    if np.ma.isMaskedArray(valid) or mask.dtype != np.dtype(bool):
        raise ValueError("valid must be an explicit Boolean mask without missing values")
    if q.ndim != 1 or not q.size or q.shape != dt.shape or q.shape != mask.shape or edges.shape != (q.size + 1,):
        raise ValueError("one flow, temperature difference and quality per interval")
    seconds = np.diff(edges)
    if not np.isfinite(edges).all() or not np.isfinite(seconds).all() or np.any(seconds <= 0):
        raise ValueError("interval edges must increase")
    use = mask & np.isfinite(q) & np.isfinite(dt) & (q >= 0)
    # Synthetic water approximation: 1 kg/L and 4.186 kJ/(kg K).
    e = np.sum(q[use] * dt[use] * seconds[use], dtype=np.float64) * 4.186 / 3600
    return {"covered_kwh": float(e), "covered_seconds": float(seconds[use].sum()),
            "total_seconds": float(seconds.sum()), "complete": bool(use.all())}


def timed_reduction(samples=9):
    if not 3 <= samples <= 25:
        raise ValueError("samples must be in 3..25")
    # Two layouts, identical values and output shape; copying excluded from timing.
    c = np.arange(512 * 1024, dtype=np.float64).reshape(512, 1024)
    f = np.asfortranarray(c)
    reduce = lambda a: a.sum(axis=1, dtype=np.float64)
    np.testing.assert_array_equal(reduce(c), reduce(f))
    traces = {"C": [], "F": []}
    for i in range(samples):
        for name, a in (("C", c), ("F", f)) if i % 2 == 0 else (("F", f), ("C", c)):
            t = perf_counter_ns()
            reduce(a)
            traces[name].append(perf_counter_ns() - t)
    return {"numpy": np.__version__, "shape": list(c.shape), "dtype": str(c.dtype),
            "axis": 1, "traces_ns": traces,
            "medians_ns": {name: median(trace) for name, trace in traces.items()}}


class Contracts(unittest.TestCase):
    def test_view(self):
        self.assertEqual(memory_contract(),
                         {"shape": [3, 2], "strides_bytes": [16, -8],
                          "view_aliases": True, "advanced_index_aliases": False})

    def test_telemetry_mask_and_one_channel_contract(self):
        result, count = telemetry_contract([[2, 4], [np.nan, 8]], [2, 0])
        np.testing.assert_allclose(result, [[1, np.nan], [np.nan, np.nan]], equal_nan=True)
        np.testing.assert_array_equal(count, [1, 0])
        with self.assertRaises(ValueError):
            telemetry_contract([[1, 2], [3, 4]], [[2], [4]])

    def test_accumulator(self):
        result = accumulator_contract()
        self.assertEqual((result["narrow"], result["wide"], result["fsum_reference"]),
                         (-25536, 40000, 1.0))

    def test_calibration(self):
        result = calibration_contract()
        self.assertEqual(result["rank"], 2)
        np.testing.assert_allclose([result["gain"], result["offset"]], [1.05, 2.0],
                                   rtol=1e-12, atol=1e-12)
        self.assertLess(result["residual_l2_degC"], 1e-10)

    def test_energy_coverage_and_nonmonotonic_rejection(self):
        result = energy_contract([1, 1], [1, 1], [0, 30, 90], [True, False])
        self.assertFalse(result["complete"])
        self.assertEqual((result["covered_seconds"], result["total_seconds"]), (30, 90))
        self.assertAlmostEqual(result["covered_kwh"], 4.186 * 30 / 3600)
        with self.assertRaises(ValueError):
            energy_contract([1, 1], [1, 1], [0, 30, 29], [True, True])

    def test_energy_mask_is_explicit_and_zero_flow_is_measured(self):
        good = energy_contract([1], [1], [0, 30], [True])
        self.assertTrue(good["complete"])
        self.assertEqual(good["covered_seconds"], 30)
        self.assertAlmostEqual(good["covered_kwh"], 4.186 * 30 / 3600)
        for flow, mask, complete, covered in ((1, [False], False, 0),
                                              (0, np.array([True]), True, 30)):
            with self.subTest(flow=flow, complete=complete):
                result = energy_contract([flow], [1], [0, 30], mask)
                self.assertEqual(result, dict(covered_kwh=0.0, covered_seconds=covered,
                                              total_seconds=30.0, complete=complete))
        for mask in ([np.nan], [1], [None], np.array([True], dtype=object),
                     np.ma.array([True], mask=[True])):
            with self.subTest(mask=mask), self.assertRaisesRegex(ValueError, "Boolean mask"):
                energy_contract([1], [1], [0, 30], mask)

    def test_benchmark_reports_raw_samples(self):
        result = timed_reduction(3)
        self.assertEqual(result["shape"], [512, 1024])
        self.assertTrue(all(len(trace) == 3 and min(trace) > 0 for trace in result["traces_ns"].values()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true")
    mode.add_argument("--benchmark", action="store_true")
    args = p.parse_args()
    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
        return int(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if args.benchmark:
        result = timed_reduction()
    else:
        normalized, counts = telemetry_contract([[2., 4.]], [2., 4.])
        result = {"memory": memory_contract(), "telemetry": normalized.tolist(),
                  "valid_per_channel": counts.tolist(), "precision": accumulator_contract(),
                  "calibration": calibration_contract(),
                  "energy": energy_contract([1, 1], [1, 1], [0, 30, 90], [True, False])}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
