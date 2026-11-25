"""離線排程實驗：Python 3.11+；只在記憶體 SQLite 寫入合成彙總。"""
from argparse import ArgumentParser
from contextlib import closing
from datetime import date, datetime, time, timedelta, timezone
import json
import sqlite3
import unittest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class DemoRetryable(RuntimeError):
    """教學注入的可重試例外。"""


def daily_bounds(logical_date, zone):
    """以行政日的兩個本地午夜建立 [start,end)，再各自轉 UTC。"""
    d = date.fromisoformat(logical_date)
    zone = ZoneInfo(zone)
    return tuple(datetime.combine(day, time.min, zone).astimezone(timezone.utc)
                 for day in (d, d + timedelta(days=1)))


def prepare(db):
    db.executescript("""
    CREATE TABLE run_ledger(run_key TEXT PRIMARY KEY, attempts INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('retryable','done')));
    CREATE TABLE daily_summary(run_key TEXT PRIMARY KEY, units INTEGER NOT NULL);
    """)


def rollback_if_open(db):
    if db.in_transaction:
        db.rollback()


def run(db, logical_date, zone="UTC", fail_for_demo=False):
    start, end = daily_bounds(logical_date, zone)
    key = f"daily-summary:v1:{zone}:{start.isoformat()}:{end.isoformat()}"
    try:
        # 只示範短的本機 transaction，不在持鎖期間等外部網路。
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT status FROM run_ledger WHERE run_key=?",
                         (key,)).fetchone()
        if old and old[0] == "done":
            db.commit()
            return {"result": "duplicate_skipped", "run_key": key}
        db.execute("INSERT INTO run_ledger VALUES (?,1,'retryable') "
                   "ON CONFLICT(run_key) DO UPDATE SET attempts=attempts+1", (key,))
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        # 若兩個 caller 交錯，前者已提交時後者不再寫。
        status = db.execute("SELECT status FROM run_ledger WHERE run_key=?",
                            (key,)).fetchone()[0]
        if status == "done":
            db.commit()
            return {"result": "duplicate_skipped", "run_key": key}
        db.execute("INSERT INTO daily_summary VALUES (?,?)", (key, 42))
        if fail_for_demo:
            raise DemoRetryable("合成錯誤：結果與完成狀態都不能提交")
        db.execute("UPDATE run_ledger SET status='done' WHERE run_key=?", (key,))
        db.commit()
    except DemoRetryable:
        rollback_if_open(db)
        return {"result": "retryable", "run_key": key}
    except BaseException:
        rollback_if_open(db)
        raise
    return {"result": "committed", "run_key": key,
            "utc_duration_hours": (end - start).total_seconds() / 3600}


class Tests(unittest.TestCase):
    def test_restart_and_replay(self):
        with closing(sqlite3.connect(":memory:", isolation_level=None)) as db:
            prepare(db)
            self.assertEqual(run(db, "2025-03-09", fail_for_demo=True)["result"], "retryable")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0], 0)
            self.assertEqual(run(db, "2025-03-09")["result"], "committed")
            self.assertEqual(run(db, "2025-03-09")["result"], "duplicate_skipped")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT attempts,status FROM run_ledger").fetchone(),
                             (2, "done"))

    def test_separate_intervals(self):
        with closing(sqlite3.connect(":memory:", isolation_level=None)) as db:
            prepare(db)
            for day in ("2025-03-09","2025-03-10"):
                self.assertEqual(run(db, day)["result"], "committed")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0], 2)

    def test_dst(self):
        try:
            pairs = [daily_bounds(day, "America/New_York")
                     for day in ("2025-03-09", "2025-11-02")]
        except ZoneInfoNotFoundError:
            self.skipTest("沒有 IANA time zone資料；請依部署政策提供時區資料")
        self.assertEqual([(end-start).total_seconds()/3600 for start,end in pairs], [23,25])


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true")
    p.add_argument("--date", default="2025-03-09", help="邏輯日 YYYY-MM-DD")
    p.add_argument("--zone", default="UTC", help="IANA 時區名稱")
    args = p.parse_args()
    if args.test:
        tests = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        return 0 if unittest.TextTestRunner().run(tests).wasSuccessful() else 1
    try:
        with closing(sqlite3.connect(":memory:", isolation_level=None)) as db:
            prepare(db)
            stages = [run(db, args.date, args.zone, fail_for_demo=i == 0) for i in range(3)]
            print(json.dumps({"stages": stages, "stored_rows": db.execute(
                "SELECT COUNT(*) FROM daily_summary").fetchone()[0]}, ensure_ascii=False, indent=2))
    except (ValueError, ZoneInfoNotFoundError) as error:
        p.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
