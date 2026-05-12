from __future__ import annotations

import sqlite3

SCHEMA_VERSION = "20260513_001"


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (length(trim(title)) > 0),
            CHECK (status IN ('open', 'done', 'archived'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_status ON notes(status)")
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    conn.commit()
