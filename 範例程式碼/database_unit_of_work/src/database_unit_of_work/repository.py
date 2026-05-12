from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class Note:
    id: int
    title: str
    status: str


class NoteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, title: str, status: str = "open") -> Note:
        cursor = self._conn.execute(
            "INSERT INTO notes(title, status) VALUES (?, ?)",
            (title, status),
        )
        return Note(id=int(cursor.lastrowid), title=title, status=status)

    def list_by_status(self, status: str = "open") -> list[Note]:
        rows = self._conn.execute(
            "SELECT id, title, status FROM notes WHERE status = ? ORDER BY id",
            (status,),
        ).fetchall()
        return [self._map_row(row) for row in rows]

    def mark_done(self, note_id: int) -> None:
        self._conn.execute(
            "UPDATE notes SET status = 'done' WHERE id = ?",
            (note_id,),
        )

    @staticmethod
    def _map_row(row: sqlite3.Row) -> Note:
        return Note(id=int(row["id"]), title=str(row["title"]), status=str(row["status"]))
