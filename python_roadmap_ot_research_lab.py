"""離線 OT 教學實驗：合成資料與既有教材 pcap；不連線、不掃描、不寫設備。"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sqlite3
import struct
import unittest

ROOT = Path(__file__).resolve().parent
CAPTURE = ROOT / "wireshark_research_sample.pcap"


def protocol() -> dict:
    # 同一 Modbus PDU 位址採 0-based；40001 只是手冊常見的表示。
    register = 235
    points = [
        {"channel": "Modbus", "value": register / 10, "source_ts": None, "state": "GOOD"},
        {"channel": "OPC UA", "value": 23.5, "source_ts": "2026-11-26T04:00:00Z", "state": "GOOD"},
        {"channel": "BACnet", "value": 23.5, "source_ts": None, "state": "GOOD"},
        {"channel": "MQTT 下游", "value": 23.5, "source_ts": None, "state": "STALE"},
    ]
    return {"synthetic": True, "unit": "°C", "pdu_offset": 0, "rows": points,
            "usable_for_kpi": sum(p["state"] == "GOOD" for p in points)}


def gateway() -> dict:
    rows = [("boot-a:1", 21.5), ("boot-a:2", 24.9)]
    publisher = sqlite3.connect(":memory:")
    consumer = sqlite3.connect(":memory:")
    try:
        publisher.execute("CREATE TABLE outbox (id TEXT PRIMARY KEY, v REAL NOT NULL)")
        consumer.execute("CREATE TABLE samples (id TEXT PRIMARY KEY, v REAL NOT NULL)")
        with publisher:
            publisher.executemany("INSERT INTO outbox VALUES (?,?)", rows)
        deliveries = 0
        def deliver(delete_after_ack: bool) -> None:
            nonlocal deliveries
            for event_id, value in publisher.execute("SELECT id,v FROM outbox ORDER BY id").fetchall():
                with consumer:
                    consumer.execute("INSERT INTO samples VALUES (?,?) ON CONFLICT(id) DO NOTHING",
                                     (event_id, value))
                deliveries += 1
                if delete_after_ack:
                    # 教學假設 durable application ACK 在 consumer commit 後回傳。
                    with publisher:
                        publisher.execute("DELETE FROM outbox WHERE id=?", (event_id,))
        deliver(False)  # 模擬消費端已提交，但確認遺失。
        waiting_before_retry = publisher.execute("SELECT count(*) FROM outbox").fetchone()[0]
        deliver(True)
        return {"messages_delivered": deliveries, "durable_rows": consumer.execute(
            "SELECT count(*) FROM samples").fetchone()[0],
            "waiting_before_retry": waiting_before_retry,
            "waiting_after_app_ack": publisher.execute("SELECT count(*) FROM outbox").fetchone()[0]}
    finally:
        consumer.close()
        publisher.close()


def pcap_metadata(raw: bytes) -> dict:
    kinds = {b"\xd4\xc3\xb2\xa1": ("<", 1_000_000), b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
             b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000), b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000)}
    if len(raw) < 24 or raw[:4] not in kinds:
        raise ValueError("需要完整的 classic pcap 標頭，並非 pcapng")
    order, ticks = kinds[raw[:4]]
    major, minor, _, _, snaplen, linktype = struct.unpack_from(order + "HHiiii", raw, 4)
    if (major, minor) != (2, 4) or snaplen <= 0:
        raise ValueError("不支援該 pcap 版本或快照長度")
    offset, cap_bytes, wire_bytes = 24, 0, 0
    stamps: list[int] = []
    trimmed = 0
    while offset < len(raw):
        if len(raw) - offset < 16:
            raise ValueError("紀錄標頭不完整")
        ts, fraction, captured, original = struct.unpack_from(order + "IIII", raw, offset)
        if fraction >= ticks or captured > original or captured > snaplen or offset + 16 + captured > len(raw):
            raise ValueError("時間精度或封包長度無效")
        offset += 16 + captured
        cap_bytes += captured
        wire_bytes += original
        trimmed += captured < original
        stamps.append(ts * ticks + fraction)
    return {"sha256": sha256(raw).hexdigest(), "frames": len(stamps), "recorded_bytes": cap_bytes,
            "original_bytes_of_recorded_frames": wire_bytes, "snaplen": snaplen,
            "linktype": linktype, "sliced_frames": trimmed,
            "timestamp_regressions": sum(b < a for a, b in zip(stamps, stamps[1:])),
            "wire_drops": None}


def congestion() -> dict:
    # 互動式排程教學：同一串列匯流排，不嘗試並行傳送。
    def scenario(timeout_ms: int) -> dict:
        finish_ms = 0
        good_finish: list[int] = []
        counts: Counter[str] = Counter()
        for outcome in ("ok", "timeout", "ok", "ok", "ok", "ok"):
            finish_ms += 25 if outcome == "ok" else timeout_ms
            counts[outcome] += 1
            if outcome == "ok":
                good_finish.append(finish_ms)
        return {"scan_ms": finish_ms, "last_good_ms": good_finish[-1],
                "good_p95_from_scan_start_ms": sorted(good_finish)[ceil(.95 * len(good_finish)) - 1],
                "success": counts["ok"], "timeouts": counts["timeout"]}
    return {"slow_budget_600": scenario(600), "bounded_budget_200": scenario(200)}


def datacenter() -> dict:
    # 兩個等長配對窗：冷凝熱不能加上已計過的 CDU 上游熱。
    windows = [(0.5, 10.0, 8.0, 2.5), (0.5, 20.0, 12.0, 3.5)]
    k = 1000 * 4.186 / 3600
    paired = sum(h * flow * dt * k for h, flow, dt, _ in windows)
    average_shortcut = k * (10 + 20) / 2 * (8 + 12) / 2
    electric = sum(h * kw for h, _, _, kw in windows)
    return {"paired_kwh_th": paired, "invalid_shortcut_kwh_th": average_shortcut,
            "cdu_kwh_e": electric, "paired_intensity": electric / paired,
            "shortcut_intensity": electric / average_shortcut}


def iso50001() -> dict:
    baseline_intercept = 600.0
    slope = 0.4
    before_units, now_units = 1000, 1200
    before_kwh, actual_kwh = 1000.0, 1030.0
    adjusted = baseline_intercept + slope * now_units
    saving = adjusted - actual_kwh
    return {"baseline_kwh": before_kwh, "baseline_units": before_units,
            "reporting_kwh": actual_kwh, "reporting_units": now_units,
            "unadjusted_change_kwh": actual_kwh - before_kwh,
            "adjusted_baseline_kwh": adjusted, "estimated_saving_kwh": saving,
            "estimated_saving_pct": 100 * saving / adjusted,
            "assumption": "示例模型已給定；未提供殘差或量測不確定度，不判定顯著改善"}


CASES = {"protocol": protocol, "gateway": gateway, "wireshark": lambda: pcap_metadata(CAPTURE.read_bytes()),
         "congestion": congestion, "datacenter": datacenter, "iso50001": iso50001}


class Tests(unittest.TestCase):
    def test_protocol_status_not_value(self):
        self.assertEqual(protocol()["usable_for_kpi"], 3)

    def test_ack_loss_does_not_duplicate_rows(self):
        self.assertEqual(gateway(), {"messages_delivered": 4, "durable_rows": 2,
                                    "waiting_before_retry": 2, "waiting_after_app_ack": 0})

    def test_pcap_metadata_and_abbreviated_file(self):
        raw = CAPTURE.read_bytes()
        result = pcap_metadata(raw)
        self.assertGreater(result["frames"], 0)
        self.assertIsNone(result["wire_drops"])
        self.assertEqual(result["sha256"], sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            pcap_metadata(raw[:-1])

    def test_congestion_reduces_wait_without_more_losses_in_sim(self):
        r = congestion()
        self.assertEqual(r["slow_budget_600"]["scan_ms"], 725)
        self.assertEqual(r["bounded_budget_200"]["scan_ms"], 325)
        self.assertEqual(r["bounded_budget_200"]["success"], 5)

    def test_datacenter_paired_product(self):
        r = datacenter()
        self.assertAlmostEqual(r["paired_kwh_th"], 186.04444444444445)
        self.assertAlmostEqual(r["invalid_shortcut_kwh_th"], 174.41666666666666)
        self.assertAlmostEqual(r["cdu_kwh_e"], 3.0)

    def test_iso_normalized_sign(self):
        r = iso50001()
        self.assertEqual(r["unadjusted_change_kwh"], 30)
        self.assertEqual(r["estimated_saving_kwh"], 50)
        self.assertAlmostEqual(r["estimated_saving_pct"], 4.6296296296)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case", nargs="?", default="all", choices=(*CASES, "all"))
    p.add_argument("--test", action="store_true")
    opts = p.parse_args()
    if opts.test:
        tests = {
            "protocol": "test_protocol_status_not_value",
            "gateway": "test_ack_loss_does_not_duplicate_rows",
            "wireshark": "test_pcap_metadata_and_abbreviated_file",
            "congestion": "test_congestion_reduces_wait_without_more_losses_in_sim",
            "datacenter": "test_datacenter_paired_product",
            "iso50001": "test_iso_normalized_sign",
        }
        suite = (unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
                 if opts.case == "all" else unittest.TestSuite([Tests(tests[opts.case])]))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    result = {key: fn() for key, fn in CASES.items()} if opts.case == "all" else CASES[opts.case]()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
