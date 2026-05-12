from __future__ import annotations

from pathlib import Path
import tempfile

from .service import NoteService


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        database_path = Path(tmpdir) / "notes.db"
        service = NoteService(database_path)
        service.create_note("write migration checklist")
        service.create_note("review rollback plan")
        for note in service.list_open_notes():
            print(f"{note.id}: {note.title} [{note.status}]")


if __name__ == "__main__":
    main()
