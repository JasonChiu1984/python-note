import runpy
from pathlib import Path

import pytest

demo = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                          "extensions/python_logging_persistence_research_tutorial/example.py"))


def test_explicit_rollback_keeps_cursor_and_readings_consistent_after_reopen(tmp_path):
    path = tmp_path / "state.db"
    conn = demo["open_db"](path)
    try:
        with pytest.raises(RuntimeError, match="4–6"):
            demo["process"](conn, crash_after=5)
    finally:
        conn.close()

    conn = demo["open_db"](path)
    try:
        assert conn.execute("SELECT last_seq FROM checkpoint").fetchone() == (3,)
        assert conn.execute("SELECT seq FROM reading ORDER BY seq").fetchall() == [(1,), (2,), (3,)]
        assert demo["process"](conn) == 3
        assert conn.execute("SELECT last_seq FROM checkpoint").fetchone() == (10,)
        assert conn.execute("SELECT seq FROM reading ORDER BY seq").fetchall() == [(i,) for i in range(1, 11)]
        assert demo["process"](conn) == 10
        assert conn.execute("SELECT count(*) FROM reading").fetchone() == (10,)
    finally:
        conn.close()
