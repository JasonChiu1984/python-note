"""Python 3.10+ 離線研究：有界 log 佇列、JSON 快照與 SQLite 狀態。"""
from argparse import ArgumentParser
from contextlib import closing
from datetime import datetime, timezone
import json
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
import os
from pathlib import Path
from queue import Full, Queue
import sqlite3
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Lock
import unittest


class CountedQueueHandler(QueueHandler):
    """本實驗的溢出契約：丟棄新事件並另計數；不回到同一 logger。"""
    def __init__(self, q):
        super().__init__(q)
        self.dropped = 0
        self.counter_lock = Lock()

    def enqueue(self, record):
        try:
            self.queue.put_nowait(record)
        except Full:
            with self.counter_lock:
                self.dropped += 1


class JSONEvent(logging.Formatter):
    """只輸出白名單欄位，不輸出任意 msg、headers、憑證或內建例外文字。"""
    def format(self, record):
        result = {
            "ts_utc": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": "sample_finished",
            "run_id": record.run_id,
        }
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


def write_snapshot(path, payload):
    # tmp 與目標同目錄，同一檔案系統。實驗不保證斷電耐久性或多 writer。
    temp = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                prefix=".snapshot-", delete=False) as stream:
            temp = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def insert_state(db, batch_id, amount):
    with db:
        return db.execute("INSERT INTO state VALUES(?,?) ON CONFLICT(batch_id) DO NOTHING",
                          (batch_id, amount)).rowcount


def experiment(root):
    q = Queue(maxsize=2)
    producer = CountedQueueHandler(q)
    sink = RotatingFileHandler(root / "events.jsonl", encoding="utf-8",
                              maxBytes=65_536, backupCount=2)
    sink.setFormatter(JSONEvent())
    logger = logging.Logger("offline-demo")
    logger.addHandler(producer)
    listener = QueueListener(q, sink, respect_handler_level=True)
    # 消費端尚未啟動，故意產生可重現的飽和，非吞吐 benchmark。
    try:
        for run_id in range(5):
            logger.info("合成欄位不可外洩", extra={"run_id": run_id})
        listener.start()
        q.join()  # 此實驗的 writer 正常運作；正式服務還須停機上限與健康訊號。
        listener.stop()
    finally:
        logger.removeHandler(producer)
        producer.close()
        sink.close()
    events = [json.loads(line) for line in (root/"events.jsonl").read_text(
        encoding="utf-8").splitlines()]
    write_snapshot(root / "summary.json", {"accepted": len(events), "dropped": producer.dropped})
    with closing(sqlite3.connect(root / "state.sqlite3")) as db:
        db.execute("CREATE TABLE state(batch_id TEXT PRIMARY KEY, amount INTEGER NOT NULL)")
        first, replay = insert_state(db, "batch-1", 42), insert_state(db, "batch-1", 42)
        state = db.execute("SELECT COUNT(*),sum(amount) FROM state").fetchone()
    return {"events": events, "dropped": producer.dropped,
            "first_insert": first, "replayed_inserts": replay, "state": state}


class Tests(unittest.TestCase):
    def test_bounded_queue_and_privacy(self):
        with TemporaryDirectory() as directory:
            result = experiment(Path(directory))
            self.assertEqual([x["run_id"] for x in result["events"]], [0, 1])
            self.assertEqual(result["dropped"], 3)
            self.assertNotIn("合成欄位不可外洩", (Path(directory)/"events.jsonl").read_text())
            self.assertEqual(result["state"], (1, 42))
            self.assertEqual(result["replayed_inserts"], 0)

    def test_failed_snapshot_keeps_previous_value(self):
        with TemporaryDirectory() as directory:
            p = Path(directory)/"snapshot.json"
            write_snapshot(p, {"count": 2})
            with self.assertRaises(ValueError):
                write_snapshot(p, {"count": float("nan")})
            self.assertEqual(json.loads(p.read_text()), {"count": 2})
            self.assertEqual(sorted(x.name for x in p.parent.iterdir()), ["snapshot.json"])

    def test_database_state_survives_reopen(self):
        with TemporaryDirectory() as directory:
            p = Path(directory)/"state.sqlite3"
            with closing(sqlite3.connect(p)) as db:
                db.execute("CREATE TABLE state(batch_id TEXT PRIMARY KEY, amount INTEGER NOT NULL)")
                self.assertEqual(insert_state(db, "batch-1", 42), 1)
            with closing(sqlite3.connect(p)) as db:
                self.assertEqual(insert_state(db, "batch-1", 99), 0)
                self.assertEqual(db.execute("SELECT amount FROM state").fetchone(), (42,))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        return 0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1
    with TemporaryDirectory(prefix="logging-research-") as d:
        print(json.dumps(experiment(Path(d)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
