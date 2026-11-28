"""安全預設：參數化 SQL 防注入、路徑穿越防護、秘密不進日誌（標準函式庫）。"""
import logging
import re
import sqlite3
import sys
from pathlib import Path

db = sqlite3.connect(":memory:")
db.executescript("CREATE TABLE point(name TEXT, value REAL); "
                 "INSERT INTO point VALUES ('AHU1_SAT', 22.5), ('AHU2_SAT', 23.1), ('ADMIN_PW', 0);")

evil = "AHU1_SAT' OR '1'='1"
unsafe = db.execute(f"SELECT name FROM point WHERE name = '{evil}'").fetchall()
safe = db.execute("SELECT name FROM point WHERE name = ?", (evil,)).fetchall()
print(f"字串拼接查詢回傳 {len(unsafe)} 筆（注入成功）；參數化查詢回傳 {len(safe)} 筆")

BASE = Path("/srv/bms/reports").resolve()


def safe_path(user_input: str) -> Path:
    p = (BASE / user_input).resolve()
    if not p.is_relative_to(BASE):
        raise PermissionError(f"拒絕存取報表目錄以外的路徑：{user_input}")
    return p


for name in ("2026-11.csv", "../../../etc/passwd", "sub/../2026-10.csv"):
    try:
        print("允許：", safe_path(name))
    except PermissionError as e:
        print(e)


class Redact(logging.Filter):
    PATTERN = re.compile(r"(password|token|api_key)=([^\s&]+)", re.I)

    def filter(self, record):
        record.msg = self.PATTERN.sub(r"\1=***", str(record.msg))
        return True


log = logging.getLogger("gw")
h = logging.StreamHandler(sys.stdout)
h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
h.addFilter(Redact())
log.addHandler(h)
log.setLevel(logging.INFO)
log.info("connect host=10.0.0.5 user=bms password=Bms#2026! token=abc123")
