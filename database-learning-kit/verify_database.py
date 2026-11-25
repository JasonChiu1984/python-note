"""Run once against a fresh disposable schema; never target production."""
import argparse
import os
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4


def connect(engine):
    if engine == "mysql":
        import mysql.connector as db

        conn = db.connect(
            host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "3306")),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], autocommit=False,
            ssl_ca=os.environ["DB_CA"], ssl_verify_cert=True, ssl_verify_identity=True,
        )
        return conn, db.IntegrityError
    if engine == "sqlserver":
        import pyodbc as db

        # Use SQL Server ODBC Driver 18; enable encryption and validate the certificate.
        return db.connect(os.environ["DB_ODBC"], autocommit=False), db.IntegrityError
    import psycopg as db

    # Supply sslmode=verify-full and sslrootcert in PG settings for remote use.
    return db.connect(os.environ["DB_DSN"], autocommit=False), db.IntegrityError


class ReadingRepository:
    def __init__(self, cursor, namespace, marker):
        self.cursor = cursor
        self.ns = namespace  # selected from source-code constants only
        self.marker = marker

    def insert(self, device_id, observed_at, temperature):
        params = ", ".join([self.marker] * 3)
        self.cursor.execute(
            f"INSERT INTO {self.ns}lab_reading "
            f"(device_id, observed_at, temperature_c) VALUES ({params})",
            (device_id, observed_at, temperature),
        )

    def audit(self, event_id, device_id, observed_at):
        params = ", ".join([self.marker] * 3)
        self.cursor.execute(
            f"INSERT INTO {self.ns}lab_audit "
            f"(event_id, device_id, observed_at) VALUES ({params})",
            (event_id, device_id, observed_at),
        )

    def exists(self, table, key, value):
        # Table/column come from these exact allowlisted pairs.
        if (table, key) not in {("lab_reading", "device_id"), ("lab_audit", "event_id")}:
            raise ValueError("unsupported check")
        self.cursor.execute(
            f"SELECT COUNT(*) FROM {self.ns}{table} WHERE {key} = {self.marker}",
            (value,),
        )
        return self.cursor.fetchone()[0] > 0


def save_reading(conn, repo, device_id, observed_at, value, event_id):
    try:
        repo.insert(device_id, observed_at, value)
        repo.audit(event_id, device_id, observed_at)
        conn.commit()
    except Exception:
        # If rollback itself fails, the caller closes/discards the connection.
        # A network error during COMMIT can leave the outcome unknown.
        conn.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("mysql", "sqlserver", "postgresql", "timescale"))
    args = parser.parse_args()
    ns = {"mysql": "", "sqlserver": "dbo.", "postgresql": "public.", "timescale": "public."}
    marker = "?" if args.engine == "sqlserver" else "%s"
    now = datetime.now(UTC)
    if args.engine == "mysql":
        now = now.replace(tzinfo=None)  # DATETIME uses the app's UTC contract
    if args.engine == "sqlserver":
        # ISO 8601 string with explicit offset, converted to datetimeoffset by SQL Server.
        now = now.isoformat(timespec="microseconds")
    event_id = str(uuid4())
    conn, conflict = connect(args.engine)
    with closing(conn), closing(conn.cursor()) as cur:
        if args.engine == "sqlserver":
            cur.execute("SET XACT_ABORT ON")
        repo = ReadingRepository(cur, ns[args.engine], marker)
        save_reading(conn, repo, 101, now, Decimal("12.50"), event_id)
        try:
            # A fresh reading passes first; duplicate audit PK must roll it back.
            save_reading(conn, repo, 102, now, Decimal("13.25"), event_id)
        except conflict:
            pass
        else:
            raise RuntimeError("expected duplicate audit primary key")
        if not repo.exists("lab_reading", "device_id", 101):
            raise RuntimeError("committed reading is missing")
        if not repo.exists("lab_audit", "event_id", event_id):
            raise RuntimeError("committed audit is missing")
        if repo.exists("lab_reading", "device_id", 102):
            raise RuntimeError("second reading leaked through rollback")
        conn.rollback()  # end the verification's read transaction explicitly
    print(f"PASS {args.engine}: commit visible, duplicate audit rolled back reading")


if __name__ == "__main__":
    main()
