"""離線 SQLite 合成示範；只使用記憶體，Python 3.10+。"""
import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
import sqlite3
import unittest

DDL = """
CREATE TABLE meter (
    meter_id TEXT PRIMARY KEY
);
CREATE TABLE event (
    event_id TEXT PRIMARY KEY,
    meter_id TEXT NOT NULL REFERENCES meter(meter_id),
    occurred_at TEXT NOT NULL,
    amount_wh INTEGER NOT NULL CHECK (amount_wh >= 0)
);
CREATE INDEX event_by_meter ON event(meter_id);
"""


@contextmanager
def database():
    """交易與連線生命週期分開；每條新連線啟用 FK。"""
    with closing(sqlite3.connect(":memory:", isolation_level=None, timeout=2)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(DDL)
        conn.executemany("INSERT INTO meter VALUES (?)", [("M-01",), ("M-02",)])
        yield conn


@contextmanager
def transaction(conn):
    """本例使用 SQLite 的明確交易控制；不搭配其他隱含交易模式。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def save_batch(conn, rows):
    """同事件 ID 的相同資料可重送，內容有差異則拒絕並回滾整批。"""
    inserted = 0
    with transaction(conn):
        for event_id, meter_id, at, amount_wh in rows:
            if at.utcoffset() is None:
                raise ValueError("事件時間需要時區")
            if type(amount_wh) is not int or amount_wh < 0:
                raise ValueError("Wh 必須是非負整數")
            persisted = (meter_id, at.astimezone(timezone.utc).isoformat(), amount_wh)
            with closing(conn.execute(
                "INSERT INTO event VALUES (?, ?, ?, ?) "
                "ON CONFLICT(event_id) DO NOTHING", (event_id, *persisted)
            )) as cursor:
                inserted += cursor.rowcount
            with closing(conn.execute(
                "SELECT meter_id, occurred_at, amount_wh FROM event WHERE event_id = ?",
                (event_id,),
            )) as cursor:
                if cursor.fetchone() != persisted:
                    raise ValueError(f"事件 ID 的內容不一致：{event_id}")
    return inserted


def meter_totals(conn, sort="meter"):
    # SQL 的識別字不是值。只挑固定 SQL 片段，絕不拼接外部原字串。
    order = {"meter": "m.meter_id", "energy": "total_wh DESC, m.meter_id"}[sort]
    with closing(conn.execute(
        "SELECT m.meter_id, COALESCE(SUM(e.amount_wh), 0) AS total_wh "
        "FROM meter m LEFT JOIN event e ON e.meter_id = m.meter_id "
        "GROUP BY m.meter_id ORDER BY " + order
    )) as cursor:
        return cursor.fetchall()


AT = datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc)
ROWS = [("A", "M-01", AT, 120), ("B", "M-01", AT, 30)]


class Tests(unittest.TestCase):
    def test_idempotent_and_aggregate(self):
        with database() as conn:
            self.assertEqual(save_batch(conn, ROWS), 2)
            self.assertEqual(save_batch(conn, ROWS), 0)
            self.assertEqual(meter_totals(conn), [("M-01", 150), ("M-02", 0)])

    def test_atomic_when_late_row_invalid(self):
        with database() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                save_batch(conn, [ROWS[0], ("C", "未知表", AT, 3)])
            self.assertEqual(meter_totals(conn), [("M-01", 0), ("M-02", 0)])
            self.assertFalse(conn.in_transaction)

    def test_mismatching_duplicate(self):
        with database() as conn:
            save_batch(conn, ROWS)
            with self.assertRaises(ValueError):
                save_batch(conn, [("C", "M-01", AT, 12), ("A", "M-01", AT, 22)])
            self.assertEqual(meter_totals(conn), [("M-01", 150), ("M-02", 0)])

    def test_timezone_and_identifier(self):
        with database() as conn:
            with self.assertRaises(ValueError):
                save_batch(conn, [("A", "M-01", AT.replace(tzinfo=None), 5)])
            with self.assertRaises(KeyError):
                meter_totals(conn, "unsupported")

    def test_connection_released(self):
        with database() as conn:
            pass
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true")
    if p.parse_args().test:
        unittest.main(argv=["lab"])
    else:
        with database() as conn:
            print(json.dumps({"first_inserted": save_batch(conn, ROWS),
                              "retry_inserted": save_batch(conn, ROWS),
                              "totals_wh": meter_totals(conn)}, ensure_ascii=False))
