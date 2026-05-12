from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from database_unit_of_work.service import NoteService


class DatabaseUnitOfWorkTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self._tmpdir.name) / "notes.db"
        self.service = NoteService(self.database_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_create_and_list_open_notes(self) -> None:
        self.service.create_note("first")
        self.service.create_note("second")

        notes = self.service.list_open_notes()

        self.assertEqual([note.title for note in notes], ["first", "second"])
        self.assertEqual({note.status for note in notes}, {"open"})

    def test_unique_title_constraint_is_enforced(self) -> None:
        self.service.create_note("same")

        with self.assertRaises(sqlite3.IntegrityError):
            self.service.create_note("same")

    def test_rollback_discards_uncommitted_note(self) -> None:
        with self.assertRaises(RuntimeError):
            self.service.create_then_fail("should rollback")

        self.assertEqual(self.service.list_open_notes(), [])


if __name__ == "__main__":
    unittest.main()
