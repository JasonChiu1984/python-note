"""Outbox 模式：業務資料與待送事件同一交易寫入，派送器至少送一次，消費端以事件 ID 去重（標準函式庫 sqlite3）。"""
import json
import sqlite3


def setup():
    db = sqlite3.connect(":memory:", isolation_level=None)
    db.executescript("""
        CREATE TABLE setpoint(device TEXT PRIMARY KEY, value REAL);
        CREATE TABLE outbox(id INTEGER PRIMARY KEY, payload TEXT, sent INTEGER DEFAULT 0);
        CREATE TABLE consumed(event_id INTEGER PRIMARY KEY);
        CREATE TABLE audit(event_id INTEGER, device TEXT, value REAL);
    """)
    return db


def change_setpoint(db, device, value):
    db.execute("BEGIN")
    db.execute("INSERT INTO setpoint VALUES (?, ?) ON CONFLICT(device) DO UPDATE SET value=excluded.value", (device, value))
    db.execute("INSERT INTO outbox(payload) VALUES (?)", (json.dumps({"device": device, "value": value}),))
    db.execute("COMMIT")


def dispatch(db, deliver, crash_before_mark=False):
    for eid, payload in db.execute("SELECT id, payload FROM outbox WHERE sent=0 ORDER BY id").fetchall():
        deliver(eid, json.loads(payload))
        if crash_before_mark:
            raise RuntimeError(f"送出事件 {eid} 後、標記 sent 前崩潰")
        db.execute("UPDATE outbox SET sent=1 WHERE id=?", (eid,))


def make_consumer(db):
    def deliver(eid, event):
        try:
            db.execute("BEGIN")
            db.execute("INSERT INTO consumed VALUES (?)", (eid,))      # 主鍵衝突 = 已處理過
            db.execute("INSERT INTO audit VALUES (?, ?, ?)", (eid, event["device"], event["value"]))
            db.execute("COMMIT")
            print(f"  消費事件 {eid}：{event}")
        except sqlite3.IntegrityError:
            db.execute("ROLLBACK")
            print(f"  事件 {eid} 重送，已處理過，略過")
    return deliver


if __name__ == "__main__":
    db = setup()
    deliver = make_consumer(db)
    change_setpoint(db, "CH-01", 7.5)
    change_setpoint(db, "CH-02", 7.0)
    try:
        dispatch(db, deliver, crash_before_mark=True)
    except RuntimeError as e:
        print("派送器：", e)
    print("重啟派送器：")
    dispatch(db, deliver)
    print("outbox 未送：", db.execute("SELECT COUNT(*) FROM outbox WHERE sent=0").fetchone()[0],
          "；audit 筆數：", db.execute("SELECT COUNT(*) FROM audit").fetchone()[0])
