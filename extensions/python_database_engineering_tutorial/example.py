"""時序資料表設計：複合主鍵防重複、索引讓查詢走索引、用 EXPLAIN QUERY PLAN 驗證（標準函式庫 sqlite3）。"""
import sqlite3

db = sqlite3.connect(":memory:")
db.executescript("""
CREATE TABLE reading(
    point_id TEXT NOT NULL,
    ts       INTEGER NOT NULL,          -- UTC epoch 秒
    value    REAL,
    quality  TEXT NOT NULL CHECK (quality IN ('good','uncertain','bad')),
    PRIMARY KEY (point_id, ts)
) WITHOUT ROWID;
""")

rows = [(f"P{p:03d}", 1_795_800_000 + i * 60, 20 + (i % 10) * 0.1, "good") for p in range(50) for i in range(200)]
db.executemany("INSERT INTO reading VALUES (?,?,?,?)", rows)
print(f"寫入 {len(rows):,} 筆")

try:
    db.execute("INSERT INTO reading VALUES ('P001', 1795800000, 25.0, 'good')")
except sqlite3.IntegrityError as e:
    print("重複寫入被拒絕：", e)
db.execute("INSERT INTO reading VALUES ('P001', 1795800000, 25.0, 'good') "
           "ON CONFLICT(point_id, ts) DO UPDATE SET value=excluded.value")
print("改用 UPSERT 後的值：", db.execute("SELECT value FROM reading WHERE point_id='P001' AND ts=1795800000").fetchone()[0])

q1 = "SELECT avg(value) FROM reading WHERE point_id='P010' AND ts BETWEEN 1795800000 AND 1795803600"
q2 = "SELECT avg(value) FROM reading WHERE ts BETWEEN 1795800000 AND 1795803600"
for name, q in (("依點位＋時間", q1), ("只依時間", q2)):
    plan = " | ".join(r[3] for r in db.execute("EXPLAIN QUERY PLAN " + q))
    print(f"{name}：{plan}")
db.execute("CREATE INDEX idx_reading_ts ON reading(ts)")
print("加上時間索引後：", " | ".join(r[3] for r in db.execute("EXPLAIN QUERY PLAN " + q2)))
try:
    db.execute("INSERT INTO reading VALUES ('P999', 1, 1.0, 'ok')")
except sqlite3.IntegrityError as e:
    print("品質值不合法：", e)
