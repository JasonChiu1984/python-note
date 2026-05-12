from __future__ import annotations

from pathlib import Path
import sqlite3
from types import TracebackType

from .repository import NoteRepository
from .schema import initialize_database


class UnitOfWork:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.notes = NoteRepository(conn)
        self._committed = False

    @classmethod
    def open(cls, database_path: str | Path) -> "UnitOfWork":
        conn = sqlite3.connect(str(database_path))
        conn.row_factory = sqlite3.Row
        initialize_database(conn)
        return cls(conn)

    def __enter__(self) -> "UnitOfWork":
        self._conn.execute("BEGIN")
        return self

    def commit(self) -> None:
        self._conn.commit()
        self._committed = True

    def rollback(self) -> None:
        self._conn.rollback()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            self.rollback()
        self._conn.close()
