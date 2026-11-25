"""Python 3.10+ / standard library only. Run: python3 database_uow_walkthrough.py"""
import sqlite3
import tempfile
import unittest
from pathlib import Path


def initialize(path):
    # Schema setup is separate from business transactions.
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL UNIQUE CHECK(length(trim(title)) > 0)
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY,
            note_id INTEGER NOT NULL REFERENCES notes(id),
            action TEXT NOT NULL
        );
        ''')
    finally:
        conn.close()


class NoteRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, title):
        # Values are bound, never interpolated into SQL.
        cursor = self.conn.execute('INSERT INTO notes(title) VALUES (?)', (title,))
        return cursor.lastrowid

    def record(self, note_id):
        self.conn.execute(
            'INSERT INTO audit(note_id, action) VALUES (?, ?)',
            (note_id, 'created'),
        )


class UnitOfWork:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        # Explicit SQL transactions avoid reliance on implicit BEGIN behavior.
        self.conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        try:
            self.conn.execute('PRAGMA foreign_keys = ON')
            self.conn.execute('BEGIN IMMEDIATE')
            self.notes = NoteRepository(self.conn)
            return self
        except BaseException:
            self.conn.close()
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                try:
                    self.conn.commit()
                except BaseException:
                    self.conn.rollback()
                    raise
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
        return False  # Never hide the original business exception.


def create_note(path, title, fail_after_insert=False):
    if not isinstance(title, str) or not title.strip():
        raise ValueError('title must not be empty')
    with UnitOfWork(path) as uow:
        note_id = uow.notes.add(title)
        if fail_after_insert:
            raise RuntimeError('simulated failure before audit')
        uow.notes.record(note_id)
    # Return success only after __exit__ commits successfully.
    return note_id


def read_state(path):
    # A fresh connection proves what another reader can actually observe.
    conn = sqlite3.connect(path)
    try:
        return (conn.execute('SELECT title FROM notes ORDER BY id').fetchall(),
                conn.execute('SELECT COUNT(*) FROM audit').fetchone()[0])
    finally:
        conn.close()


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'lesson.db'
        initialize(self.db)

    def test_commit_both_writes(self):
        create_note(self.db, 'pump inspection')
        self.assertEqual(read_state(self.db), ([('pump inspection',)], 1))

    def test_failure_rolls_back_first_write(self):
        with self.assertRaises(RuntimeError):
            create_note(self.db, 'must disappear', fail_after_insert=True)
        self.assertEqual(read_state(self.db), ([], 0))

    def test_bound_parameter_is_literal_text(self):
        text = "x'); DROP TABLE notes; --"
        create_note(self.db, text)
        self.assertEqual(read_state(self.db), ([(text,)], 1))

    def test_unique_violation_rolls_back_whole_transaction(self):
        create_note(self.db, 'existing')
        with self.assertRaises(sqlite3.IntegrityError):
            with UnitOfWork(self.db) as uow:
                uow.notes.add('must disappear')
                uow.notes.add('existing')
        self.assertEqual(read_state(self.db), ([('existing',)], 1))

    def test_foreign_key_failure_rolls_back(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with UnitOfWork(self.db) as uow:
                uow.notes.add('must disappear')
                uow.notes.record(999)
        self.assertEqual(read_state(self.db), ([], 0))

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            create_note(self.db, '   ')
        self.assertEqual(read_state(self.db), ([], 0))

    def test_database_check_constraint(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with UnitOfWork(self.db) as uow:
                uow.notes.add('')
        self.assertEqual(read_state(self.db), ([], 0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
