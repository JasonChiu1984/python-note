"""Controlled, synthetic, offline PCAP observability study. No sockets or capture."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from struct import pack
import unittest

from python_offline_pcap_lab import FRAME, MAGIC, TAGGED, inspect

S_PER_EPOCH = 1_700_000_000


def epoch_ns(seconds: int, fraction: int, unit: str) -> int:
    """Keep timestamp precision as integers; do not round through a float."""
    divisors = {"us": 1_000_000, "ns": 1_000_000_000}
    if unit not in divisors or not 0 <= fraction < divisors[unit]:
        raise ValueError("Invalid timestamp unit or fraction")
    return seconds * 1_000_000_000 + fraction * (1_000_000_000 // divisors[unit])


def capture(frame: bytes, caplen: int, magic: bytes) -> bytes:
    """Represent a snaplen-limited observation of a known, complete frame."""
    if not 0 < caplen <= len(frame):
        raise ValueError("caplen must describe an observed prefix")
    order, precision = MAGIC[magic]
    # Classic PCAP v2.4, LINKTYPE_ETHERNET, observed packet prefix only.
    return (magic + pack(order + "HHIIII", 2, 4, 0, 0, caplen, 1)
            + pack(order + "IIII", S_PER_EPOCH, precision // 4, caplen, len(frame))
            + frame[:caplen])


def expected_conditions(tagged: bool) -> list[tuple[str, int, str]]:
    l3 = 18 if tagged else 14
    return [
        ("short_ethernet", 12, "truncated_ethernet"),
        ("before_l3", l3 - 1, "truncated_vlan" if tagged else "truncated_ethernet"),
        ("l3_start", l3, "truncated_ipv4_header"),
        ("before_ipv4_header_end", l3 + 19, "truncated_ipv4_header"),
        ("complete_ipv4_header_only", l3 + 20, "truncated_ipv4_datagram"),
        ("one_missing_ip_byte", l3 + 31, "truncated_ipv4_datagram"),
        ("complete_ip_no_padding", l3 + 32, "udp"),
        ("complete_frame", 64 if tagged else 60, "udp"),
    ]


def run_study() -> dict:
    rows = []
    for tagged, frame in ((False, FRAME), (True, TAGGED)):
        for marker in MAGIC:
            for scenario, length, expected in expected_conditions(tagged):
                raw = capture(frame, length, marker)
                report = inspect(raw)
                observed = report["records"][0]
                rows.append({
                    "tagged": tagged, "scenario": scenario, "container_endian": report["endian"],
                    "timestamp_unit": report["timestamp_unit"], "caplen": length,
                    "original_bytes": len(frame), "expected": expected,
                    "observed": observed["status"], "payload_bytes": observed.get("payload_length"),
                    "capture_is_partial": observed["capture_truncated"],
                    "epoch_ns": epoch_ns(observed["seconds_since_epoch"],
                                         observed["fraction"], report["timestamp_unit"]),
                    "file_sha256": sha256(raw).hexdigest(),
                })
    failures = [r for r in rows if r["expected"] != r["observed"]]
    return {"study": "offline-snaplen-v1", "conditions": len(rows),
            "matched": len(rows) - len(failures),
            "observed_status_counts": dict(Counter(r["observed"] for r in rows)),
            "rows": rows}


class TestStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_study()

    def test_full_factorial_conditions(self):
        self.assertEqual((self.report["conditions"], self.report["matched"]), (64, 64))
        self.assertEqual(self.report["observed_status_counts"], {
            "truncated_ethernet": 12, "truncated_vlan": 4, "truncated_ipv4_header": 16,
            "truncated_ipv4_datagram": 16, "udp": 16,
        })

    def test_captured_frame_incomplete_but_ipv4_udp_complete(self):
        rows = [r for r in self.report["rows"] if r["scenario"] == "complete_ip_no_padding"]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["capture_is_partial"] and r["payload_bytes"] == 4 for r in rows))

    def test_independent_container_encoding_and_wire_fields(self):
        self.assertEqual({r["container_endian"] for r in self.report["rows"]}, {"little", "big"})
        self.assertEqual({r["timestamp_unit"] for r in self.report["rows"]}, {"us", "ns"})
        self.assertEqual({r["epoch_ns"] for r in self.report["rows"]}, {1_700_000_000_250_000_000})
        for magic in MAGIC:
            record = inspect(capture(TAGGED, len(TAGGED), magic))["records"][0]
            self.assertEqual((record["vlan"], record["source_port"], record["destination_port"]),
                             (100, 12345, 8080))

    def test_timestamp_integer_precision(self):
        sec = 1_700_000_000
        self.assertEqual(epoch_ns(sec, 123, "us") - epoch_ns(sec, 123, "ns"), 122_877)
        with self.assertRaises(ValueError):
            epoch_ns(sec, 1_000_000, "us")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--cases", action="store_true", help="Include each designed condition in JSON")
    args = parser.parse_args()
    if args.test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestStudy))
        return 0 if result.wasSuccessful() else 1
    report = run_study()
    if not args.cases:
        report.pop("rows")
    print(json.dumps(report, indent=2))
    return int(report["matched"] != report["conditions"])


if __name__ == "__main__":
    raise SystemExit(main())
