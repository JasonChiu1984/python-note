"""Disposable SQLite migration lab. Run with Python 3.10+: python3 sqlite_data_evolution_lab.py"""
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

V1 = "CREATE TABLE readings(id INTEGER PRIMARY KEY CHECK(id > 0), c INTEGER NOT NULL CHECK(typeof(c)='integer' AND c BETWEEN -40 AND 100))"
V3 = "CREATE TABLE readings_next(id INTEGER PRIMARY KEY CHECK(id > 0), deci_c INTEGER NOT NULL CHECK(typeof(deci_c)='integer' AND deci_c BETWEEN -400 AND 1000))"


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=3, isolation_level=None)
    try:
        yield db
    finally:
        db.close()


@contextmanager
def write_transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield
        db.execute('COMMIT')
    except BaseException:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise


def version(db):
    return db.execute('PRAGMA user_version').fetchone()[0]


def initialize(db):
    with write_transaction(db):
        db.execute(V1)
        db.executemany('INSERT INTO readings(c) VALUES (?)', [(18,), (22,), (27,)])
        db.execute('PRAGMA user_version = 1')


def expand(db):
    with write_transaction(db):
        if version(db) == 2:
            return
        if version(db) != 1 or db.execute(
            "PRAGMA table_info(readings)"
        ).fetchall() != [(0, 'id', 'INTEGER', 0, None, 1),
                         (1, 'c', 'INTEGER', 1, None, 0)]:
            raise RuntimeError('unexpected schema; stop')
        db.execute("""ALTER TABLE readings ADD COLUMN deci_c INTEGER
            CHECK(deci_c IS NULL OR (typeof(deci_c)='integer'
            AND deci_c BETWEEN -400 AND 1000 AND deci_c = c * 10))""")
        db.execute('CREATE TABLE migration_state(name TEXT PRIMARY KEY, last_id INTEGER NOT NULL)')
        db.execute("INSERT INTO migration_state VALUES ('c_to_deci_c', 0)")
        # Deployment precondition: drain all legacy writers.
        db.execute('PRAGMA user_version = 2')


def compat_write(db, row_id, c):
    """Only V2 writes are allowed by the deployment gate during the lab window."""
    with write_transaction(db):
        if version(db) != 2:
            raise RuntimeError('compat write requires expand phase')
        db.execute("""INSERT INTO readings(id,c,deci_c) VALUES (?,?,?)
            ON CONFLICT(id) DO UPDATE SET c=excluded.c,deci_c=excluded.deci_c""",
                   (row_id, c, c * 10))


def checkpoint(db):
    value = db.execute("SELECT last_id FROM migration_state WHERE name = ?", ('c_to_deci_c',)).fetchone()
    if value is None:
        raise RuntimeError('checkpoint missing; stop')
    return value[0]


def backfill_batch(db, size=2, *, simulate_interrupt=False):
    if not 1 <= size <= 1000:
        raise ValueError('size must be within 1..1000')
    with write_transaction(db):
        if version(db) != 2:
            raise RuntimeError('backfill requires expand phase')
        rows = db.execute('SELECT id FROM readings WHERE id > ? ORDER BY id LIMIT ?',
                          (checkpoint(db), size)).fetchall()
        if not rows:
            return 0
        db.executemany('UPDATE readings SET deci_c=c*10 WHERE id=? AND deci_c IS NULL', rows)
        if simulate_interrupt:
            raise RuntimeError('simulated abort before checkpoint')
        db.execute('UPDATE migration_state SET last_id=? WHERE name=?',
                   (rows[-1][0], 'c_to_deci_c'))
        return len(rows)


def validate(db):
    nulls, mismatches = db.execute("""SELECT COUNT(CASE WHEN deci_c IS NULL THEN 1 END),
          COUNT(CASE WHEN deci_c != c*10 THEN 1 END) FROM readings""").fetchone()
    if nulls or mismatches:
        raise RuntimeError(f'validation blocked: nulls={nulls}, mismatch={mismatches}')


def read_deci_c(db):
    if version(db) == 1:
        return db.execute('SELECT id,c*10 FROM readings ORDER BY id').fetchall()
    if version(db) == 3:
        return db.execute('SELECT id,deci_c FROM readings ORDER BY id').fetchall()
    return db.execute('SELECT id,COALESCE(deci_c,c*10) FROM readings ORDER BY id').fetchall()


def rollback_reader(db):
    if version(db) == 3:
        raise RuntimeError('v1 schema no longer available after contract')
    return db.execute('SELECT id,c FROM readings ORDER BY id').fetchall()


def contract(db):
    with write_transaction(db):
        if version(db) != 2:
            raise RuntimeError('contract requires expand phase')
        validate(db)
        db.execute(V3)
        db.execute('INSERT INTO readings_next SELECT id,deci_c FROM readings')
        old_count = db.execute('SELECT COUNT(*) FROM readings').fetchone()[0]
        new_count = db.execute('SELECT COUNT(*) FROM readings_next').fetchone()[0]
        if old_count != new_count:
            raise RuntimeError('row count mismatch')
        db.execute('DROP TABLE readings')
        db.execute('ALTER TABLE readings_next RENAME TO readings')
        db.execute('DROP TABLE migration_state')
        db.execute('PRAGMA user_version = 3')


def backup_to_new_file(src, target):
    """Exclusive destination, never overwrite a file. Only for the lab."""
    target = Path(target)
    with target.open('xb'):
        pass
    try:
        with connect(target) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise RuntimeError('snapshot integrity check failed')
    except BaseException:
        target.unlink()
        raise


class Lab(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        cm = connect(self.root / 'lab.db')
        self.db = cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        initialize(self.db)

    def test_drift_blocks_expand(self):
        self.db.execute('ALTER TABLE readings ADD COLUMN unexpected TEXT')
        with self.assertRaisesRegex(RuntimeError, 'schema'):
            expand(self.db)
        self.assertEqual(version(self.db), 1)

    def test_expand_is_idempotent_and_compatible(self):
        expand(self.db)
        expand(self.db)
        self.assertEqual(rollback_reader(self.db), [(1,18), (2,22), (3,27)])
        self.assertEqual(read_deci_c(self.db), [(1,180), (2,220), (3,270)])

    def test_batch_abort_then_resume_and_rerun(self):
        expand(self.db)
        self.assertEqual(backfill_batch(self.db, 1), 1)
        with self.assertRaisesRegex(RuntimeError, 'simulated'):
            backfill_batch(self.db, 1, simulate_interrupt=True)
        self.assertEqual(checkpoint(self.db), 1)
        self.assertEqual(self.db.execute('SELECT deci_c FROM readings WHERE id=2').fetchone(), (None,))
        self.assertEqual(backfill_batch(self.db), 2)
        self.assertEqual(backfill_batch(self.db), 0)
        validate(self.db)

    def test_compat_write_updates_behind_checkpoint(self):
        expand(self.db)
        backfill_batch(self.db)
        compat_write(self.db, 1, 19)
        self.assertEqual(read_deci_c(self.db)[0], (1,190))
        self.assertEqual(rollback_reader(self.db)[0], (1,19))

    def test_contract_gates_and_constraints(self):
        expand(self.db)
        with self.assertRaisesRegex(RuntimeError, 'nulls'):
            contract(self.db)
        while backfill_batch(self.db):
            pass
        contract(self.db)
        self.assertEqual(read_deci_c(self.db), [(1,180), (2,220), (3,270)])
        with self.assertRaisesRegex(RuntimeError, 'no longer'):
            rollback_reader(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('INSERT INTO readings(deci_c) VALUES (?)', (None,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('INSERT INTO readings(deci_c) VALUES (?)', (1001,))

    def test_backup_and_restore_drill(self):
        expand(self.db)
        while backfill_batch(self.db):
            pass
        snapshot = self.root / 'snapshot.db'
        backup_to_new_file(self.db, snapshot)
        contract(self.db)
        self.db.execute('UPDATE readings SET deci_c=181 WHERE id=1')
        restored = self.root / 'restore-drill.db'
        with connect(snapshot) as source:
            backup_to_new_file(source, restored)
        with connect(restored) as recovery:
            self.assertEqual(version(recovery), 2)
            self.assertEqual(rollback_reader(recovery)[0], (1,18))
        self.assertEqual(read_deci_c(self.db)[0], (1,181))  # No in-place overwrite.
        with self.assertRaises(FileExistsError):
            backup_to_new_file(self.db, restored)


if __name__ == '__main__':
    unittest.main(verbosity=2)
