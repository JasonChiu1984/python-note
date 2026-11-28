"""SQLite 交易內同時寫入事件與 checkpoint，模擬中途崩潰後重啟不重複、不跳筆（標準函式庫）。"""
import sqlite3
import tempfile
from pathlib import Path

READINGS = [(i, 20.0 + i * 0.1) for i in range(1, 11)]     # (序號, 讀值)


def open_db(path):
    con = sqlite3.connect(path, isolation_level=None)       # 手動控制交易
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS reading(seq INTEGER PRIMARY KEY, value REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS checkpoint(id INTEGER PRIMARY KEY CHECK(id=1), last_seq INTEGER)")
    con.execute("INSERT OR IGNORE INTO checkpoint VALUES (1, 0)")
    return con


def process(con, crash_after=None, batch=3):
    last = con.execute("SELECT last_seq FROM checkpoint").fetchone()[0]
    pending = [r for r in READINGS if r[0] > last]
    done = 0
    for i in range(0, len(pending), batch):
        chunk = pending[i:i + batch]
        con.execute("BEGIN")
        con.executemany("INSERT INTO reading VALUES (?, ?)", chunk)
        if crash_after is not None and done + len(chunk) > crash_after:
            con.execute("ROLLBACK")                          # 模擬交易提交前程序崩潰
            raise RuntimeError(f"在處理序號 {chunk[0][0]}–{chunk[-1][0]} 時崩潰")
        con.execute("UPDATE checkpoint SET last_seq=?", (chunk[-1][0],))
        con.execute("COMMIT")
        done += len(chunk)
    return last


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "state.db"
        con = open_db(db)
        try:
            process(con, crash_after=5)
        except RuntimeError as e:
            print("第一次執行：", e)
        con.close()
        con = open_db(db)                                   # 重啟
        n, last = con.execute("SELECT COUNT(*), (SELECT last_seq FROM checkpoint) FROM reading").fetchone()
        print(f"重啟時：已寫入 {n} 筆，checkpoint = {last}")
        resumed_from = process(con)
        rows = con.execute("SELECT seq FROM reading ORDER BY seq").fetchall()
        seqs = [r[0] for r in rows]
        print(f"從序號 {resumed_from + 1} 繼續；最後共 {len(seqs)} 筆，重複 {len(seqs) - len(set(seqs))} 筆，"
              f"缺漏 {[s for s in range(1, 11) if s not in seqs] or '無'}")
        con.close()
