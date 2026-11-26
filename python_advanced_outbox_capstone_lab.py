"""離線案例：SQLite 交易式寄件匣與消費端冪等。Python 3.11+。"""
import argparse
from contextlib import closing
import sqlite3
import unittest


def source_db():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE reports(id TEXT PRIMARY KEY, count INTEGER NOT NULL);
        CREATE TABLE outbox(id TEXT PRIMARY KEY, count INTEGER NOT NULL,
                            acknowledged INTEGER NOT NULL DEFAULT 0);
    """)
    return db


def receiver_db():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE seen(id TEXT PRIMARY KEY, count INTEGER NOT NULL);
        CREATE TABLE totals(value INTEGER NOT NULL);
        INSERT INTO totals VALUES (0);
    """)
    return db


def create_report(db, event_id, amount, *, fail=False):
    with db:
        db.execute("INSERT INTO reports VALUES (?, ?)", (event_id, amount))
        db.execute("INSERT INTO outbox(id, count) VALUES (?, ?)", (event_id, amount))
        if fail:
            raise RuntimeError("synthetic rollback")


def receive(db, event_id, amount):
    with db:
        cursor = db.execute(
            "INSERT INTO seen VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
            (event_id, amount),
        )
        if cursor.rowcount == 1:
            db.execute("UPDATE totals SET value = value + ?", (amount,))
            return True
        previous = db.execute("SELECT count FROM seen WHERE id = ?", (event_id,)).fetchone()
        if previous != (amount,):
            raise ValueError("event id reused with different payload")
        return False


def deliver(source, receiver, *, uncertain=False):
    result = []
    for event_id, count in source.execute(
        "SELECT id, count FROM outbox WHERE acknowledged = 0 ORDER BY id"
    ).fetchall():
        result.append(receive(receiver, event_id, count))
        if not uncertain:
            with source:
                source.execute("UPDATE outbox SET acknowledged = 1 WHERE id = ?", (event_id,))
    return result


class Tests(unittest.TestCase):
    def test_atomic_rollback(self):
        with closing(source_db()) as db:
            with self.assertRaises(RuntimeError):
                create_report(db, "r-1", 3, fail=True)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reports").fetchone(), (0,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone(), (0,))

    def test_ack_loss_duplicates_delivery_not_business_effect(self):
        with closing(source_db()) as source, closing(receiver_db()) as receiver:
            create_report(source, "r-1", 3)
            self.assertEqual(deliver(source, receiver, uncertain=True), [True])
            self.assertEqual(deliver(source, receiver), [False])
            self.assertEqual(deliver(source, receiver), [])
            self.assertEqual(receiver.execute("SELECT value FROM totals").fetchone(), (3,))

    def test_same_id_different_content_not_accepted(self):
        with closing(receiver_db()) as receiver:
            self.assertTrue(receive(receiver, "r-1", 3))
            with self.assertRaises(ValueError):
                receive(receiver, "r-1", 7)
            self.assertEqual(receiver.execute("SELECT value FROM totals").fetchone(), (3,))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        return 0 if unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    with closing(source_db()) as source, closing(receiver_db()) as receiver:
        create_report(source, "r-1", 3)
        print("first delivery (ack not recorded):", deliver(source, receiver, uncertain=True))
        print("retry (already applied):", deliver(source, receiver))
        print("pending after ack:", len(deliver(source, receiver)))
        print("materialized total:", receiver.execute("SELECT value FROM totals").fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
