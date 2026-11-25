"""Offline bandwidth and application-response arithmetic; never opens a socket."""

import argparse
import json
import math
import unittest


def bits_time_us(octets: int, rate_mbps: float) -> float:
    if octets < 0 or not math.isfinite(rate_mbps) or rate_mbps <= 0:
        raise ValueError("位元組數不可為負，速率須為正的有限值")
    return 8 * octets / rate_mbps


def frame_model(frame_bytes: int, rate_mbps: float, useful_bytes: int = 0) -> dict:
    """Untagged Ethernet II, standard frame size; MAC frame includes FCS."""
    if not 64 <= frame_bytes <= 1518:
        raise ValueError("本模型僅接受 64–1518 bytes 的未加標籤 MAC frame")
    if not 0 <= useful_bytes <= frame_bytes - 18:
        raise ValueError("有效資料不能超過 MAC data/padding 區域")
    occupied_bytes = frame_bytes + 8 + 12
    return {
        "frame_bytes": frame_bytes,
        "rate_mbps": rate_mbps,
        "serialize_us": bits_time_us(frame_bytes + 8, rate_mbps),
        "busy_cycle_us": bits_time_us(occupied_bytes, rate_mbps),
        "frames_per_second": rate_mbps * 1_000_000 / (8 * occupied_bytes),
        "one_way_goodput_ceiling_mbps": rate_mbps * useful_bytes / occupied_bytes,
    }


def rtt_model(rates: tuple[float, ...], request: int, response: int,
              endpoint_us: float, switching_us: float,
              propagation_us: float, queue_us: float) -> dict:
    """Serial store-and-forward path; non-serialization inputs are round totals."""
    if not rates or any(not math.isfinite(x) or x < 0 for x in
                        (endpoint_us, switching_us, propagation_us, queue_us)):
        raise ValueError("至少一段鏈路，各項延遲須為非負有限值")
    tx_us = sum(frame_model(n, rate)["serialize_us"]
                for rate in rates for n in (request, response))
    totals = dict(serialization_us=tx_us, endpoint_us=endpoint_us,
                  switching_us=switching_us, propagation_us=propagation_us,
                  queue_us=queue_us)
    return {**totals, "application_response_us": sum(totals.values())}


def example() -> dict:
    return {
        "min_frame": [frame_model(64, r) for r in (100, 1000)],
        "full_ipv4_tcp_data": [frame_model(1518, r, 1460) for r in (100, 1000)],
        "full_ipv4_udp_data": [frame_model(1518, r, 1472) for r in (100, 1000)],
        "mixed_link_rtt": rtt_model((1000, 100), 100, 120, 2400, 6, 4, 50),
        "all_gigabit_rtt": rtt_model((1000, 1000), 100, 120, 2400, 6, 4, 50),
    }


class BudgetTest(unittest.TestCase):
    def test_minimum_and_full_frames(self):
        for n, r, expect in ((64, 100, 6.72), (64, 1000, 0.672),
                             (1518, 100, 123.04), (1518, 1000, 12.304)):
            with self.subTest(frame=n, rate=r):
                self.assertAlmostEqual(frame_model(n, r)["busy_cycle_us"], expect)

    def test_payload_and_gap_accounting(self):
        v = frame_model(1518, 1000, 1460)
        self.assertAlmostEqual(v["serialize_us"], 12.208)
        self.assertAlmostEqual(v["one_way_goodput_ceiling_mbps"], 1000 * 1460 / 1538)
        self.assertAlmostEqual(frame_model(64, 100)["frames_per_second"], 100_000_000 / 672)

    def test_mixed_rate_rtt(self):
        e = example()
        self.assertAlmostEqual(e["mixed_link_rtt"]["serialization_us"], 20.768)
        self.assertAlmostEqual(e["mixed_link_rtt"]["application_response_us"], 2480.768)
        self.assertAlmostEqual(e["all_gigabit_rtt"]["application_response_us"], 2463.776)

    def test_validation(self):
        for args in ((63, 100), (1519, 100), (64, 0), (64, float("nan")), (64, 100, 47)):
            with self.assertRaises(ValueError):
                frame_model(*args)
        with self.assertRaises(ValueError):
            rtt_model((), 100, 120, 0, 0, 0, 0)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    if args.test:
        unittest.main(argv=["lab"])
    else:
        print(json.dumps(example(), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
