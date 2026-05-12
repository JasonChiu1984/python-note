from __future__ import annotations

from pathlib import Path

from .repository import Note
from .uow import UnitOfWork


class NoteService:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = database_path

    def create_note(self, title: str) -> Note:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("title must not be blank")

        with UnitOfWork.open(self._database_path) as uow:
            note = uow.notes.add(normalized_title)
            uow.commit()
            return note

    def create_then_fail(self, title: str) -> None:
        with UnitOfWork.open(self._database_path) as uow:
            uow.notes.add(title.strip())
            raise RuntimeError("simulated failure before commit")

    def list_open_notes(self) -> list[Note]:
        with UnitOfWork.open(self._database_path) as uow:
            notes = uow.notes.list_by_status("open")
            uow.commit()
            return notes
