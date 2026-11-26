"""Six independent, offline release-engineering exercises (Python 3.10+)."""
import argparse
import base64
import collections
import concurrent.futures
import csv
import hashlib
import io
import json
import re
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def check(ok, detail):
    if not ok:
        raise AssertionError(detail)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalized(name):
    if not re.fullmatch(r"[a-zA-Z0-9]+(?:[-_.]+[a-zA-Z0-9]+)*", name):
        raise ValueError("invalid distribution name")
    return re.sub(r"[-_.]+", "-", name).lower()


def snapshot(pairs):
    result = {}
    for name, version in pairs:
        key = normalized(name)
        if key in result:
            raise ValueError("ambiguous duplicate distribution")
        result[key] = version
    return result


def diff(lock, actual):
    return {
        "missing": sorted(lock.keys() - actual.keys()),
        "changed": {name: [lock[name], actual[name]]
                    for name in sorted(lock.keys() & actual.keys()) if lock[name] != actual[name]},
        "extra": sorted(actual.keys() - lock.keys()),
    }


def dependencies():
    lock = snapshot([("Factory-Core", "1.4"), ("factory-probe", "2.0"), ("factory-math", "3.0")])
    actual = snapshot([("factory_core", "1.4"), ("factory-probe", "2.1"), ("debug-tool", "0.1")])
    result = diff(lock, actual)
    check(result == {"missing": ["factory-math"], "changed": {"factory-probe": ["2.0", "2.1"]},
                     "extra": ["debug-tool"]}, "drift not recognized")
    check(diff(lock, dict(lock)) == {"missing": [], "changed": {}, "extra": []}, "clean drift")
    try:
        snapshot([("One_Pkg", "1"), ("one-pkg", "2")])
    except ValueError:
        return result
    raise AssertionError("duplicate aliases accepted")


def totals(events):
    """Collapse exact repeats; conflicting repeat IDs are data errors."""
    unique = {}
    for event_id, zone, value in events:
        fact = (zone, value)
        if event_id in unique and unique[event_id] != fact:
            raise ValueError("conflicting duplicate")
        unique[event_id] = fact
    result = collections.Counter()
    for zone, value in unique.values():
        result[zone] += value
    return dict(result)


def testing():
    rows = [(1, "a", 12), (2, "b", 7), (3, "a", 5)]
    reference = {"a": 17, "b": 7}
    variants = [rows, rows[::-1], rows + rows[:1], rows[1:] + rows[:1]]
    for variant in variants:
        check(totals(variant) == reference, "reference or metamorphic relation failed")
    try:
        totals(rows + [(1, "a", 13)])
    except ValueError:
        return {"variants_passed": len(variants), "conflict_rejected": True, "example_totals": reference}
    raise AssertionError("conflicting fact accepted")


def bounded(executor, fn, items, limit):
    if limit <= 0:
        raise ValueError("limit must be positive")
    iterator = iter(items)
    pending = set()
    maximum = 0
    results = []
    while True:
        while len(pending) < limit:
            try:
                item = next(iterator)
            except StopIteration:
                break
            pending.add(executor.submit(fn, item))
            maximum = max(maximum, len(pending))
        if not pending:
            return results, maximum
        finished, pending = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
        results.extend(future.result() for future in finished)


def concurrency():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        values, maximum = bounded(executor, abs, range(-12, 0), limit=3)
    check(sorted(values) == list(range(1, 13)), "results differ")
    check(maximum == 3, "admission limit failed")
    return {"jobs": len(values), "workers": 2, "peak_outstanding": maximum,
            "result_order": "not guaranteed"}


def persistence():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.sqlite3"
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY NOT NULL, value INTEGER NOT NULL)")
            conn.execute("CREATE TABLE state (checkpoint INTEGER NOT NULL)")
            conn.execute("INSERT INTO state VALUES (0)")
        def ingest(event_id, value, fail=False):
            with closing(sqlite3.connect(path)) as conn, conn:
                row = conn.execute("SELECT value FROM events WHERE id=?", (event_id,)).fetchone()
                if row is not None:
                    if row != (value,):
                        raise ValueError("conflicting event")
                    return "duplicate"
                checkpoint = conn.execute("SELECT checkpoint FROM state").fetchone()[0]
                if event_id != checkpoint + 1:
                    raise ValueError("cursor gap")
                conn.execute("INSERT INTO events VALUES (?,?)", (event_id, value))
                conn.execute("UPDATE state SET checkpoint=?", (event_id,))
                if fail:
                    raise RuntimeError("simulated error before commit")
                return "committed"
        check(ingest(1, 20) == "committed", "first event")
        try:
            ingest(2, 30, fail=True)
        except RuntimeError:
            pass
        with closing(sqlite3.connect(path)) as conn:
            check(conn.execute("SELECT checkpoint FROM state").fetchone() == (1,), "rollback checkpoint")
            check(conn.execute("SELECT COUNT(*) FROM events").fetchone() == (1,), "rollback event")
        states = [ingest(1, 20), ingest(2, 30)]
        with closing(sqlite3.connect(path)) as conn:
            end = conn.execute("SELECT checkpoint FROM state").fetchone()[0]
        check(states == ["duplicate", "committed"] and end == 2, "recovery")
        return {"after_error_cursor": 1, "replay": states, "final_cursor": end}


def release_gate(candidate, reports, expected_revision):
    required = ("unit", "install", "smoke")
    failures = []
    for name in required:
        matches = [report for report in reports if report.get("gate") == name]
        if len(matches) != 1:
            failures.append(name + ":count")
            continue
        entry = matches[0]
        if entry.get("outcome") != "pass":
            failures.append(name + ":outcome")
        if entry.get("sha256") != digest(candidate):
            failures.append(name + ":digest")
        if entry.get("revision") != expected_revision:
            failures.append(name + ":revision")
    return failures


def ci():
    artifact = b"offline release candidate v1"
    reports = [{"gate": gate, "outcome": "pass", "sha256": digest(artifact), "revision": "demo-r1"}
               for gate in ("unit", "install", "smoke")]
    scenarios = {"clean": release_gate(artifact, reports, "demo-r1"),
                 "missing": release_gate(artifact, reports[:-1], "demo-r1"),
                 "changed_bytes": release_gate(artifact + b"!", reports, "demo-r1"),
                 "other_revision": release_gate(artifact, reports, "demo-r2")}
    check([len(s) for s in scenarios.values()] == [0, 1, 3, 3], "unexpected release policy")
    return scenarios


def record_hash(data):
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")


def sample_wheel(changed):
    entries = {"demo_pkg/__init__.py": b"VERSION = '1.0'\n",
               "demo_pkg-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: demo-pkg\nVersion: 1.0\n\n",
               "demo_pkg-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"}
    record = "demo_pkg-1.0.dist-info/RECORD"
    csv_file = io.StringIO(newline="")
    writer = csv.writer(csv_file, lineterminator="\n")
    writer.writerows((name, record_hash(value), len(value)) for name, value in entries.items())
    writer.writerow((record, "", ""))
    if changed:
        entries["demo_pkg/__init__.py"] = b"VERSION = '9.0'\n"
    bytes_file = io.BytesIO()
    with ZipFile(bytes_file, "w") as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
        archive.writestr(record, csv_file.getvalue().encode())
    return bytes_file.getvalue()


def compare_record(blob):
    if len(blob) > 128 * 1024:
        raise ValueError("lab wheel exceeds byte limit")
    with ZipFile(io.BytesIO(blob)) as archive:
        files = archive.infolist()
        names = {info.filename for info in files}
        if (len(names) != len(files) or len(files) > 30 or
                sum(info.file_size for info in files) > 128 * 1024 or
                any(info.is_dir() or info.filename.startswith("/") or
                    ".." in PurePosixPath(info.filename).parts or "\\" in info.filename for info in files)):
            raise ValueError("duplicate, unusual path or excessive files")
        records = [name for name in names if name.endswith(".dist-info/RECORD")]
        if len(records) != 1:
            raise ValueError("expected one RECORD file")
        record = records[0]
        rows = list(csv.reader(io.StringIO(archive.read(record).decode("utf-8"), newline="")))
        if any(len(row) != 3 for row in rows):
            raise ValueError("invalid RECORD column count")
        if len(rows) != len(names) or {row[0] for row in rows} != names:
            raise ValueError("RECORD coverage differs")
        failures = []
        for name, tagged_hash, length in rows:
            if name == record:
                if tagged_hash or length:
                    failures.append(name)
                continue
            content = archive.read(name)
            if tagged_hash != record_hash(content) or length != str(len(content)):
                failures.append(name)
        return failures


def packaging():
    clean, changed = compare_record(sample_wheel(False)), compare_record(sample_wheel(True))
    check(clean == [] and changed == ["demo_pkg/__init__.py"], "RECORD drift")
    return {"valid_internal_record": clean, "changed_files": changed,
            "proof_of_origin": False}


CASES = {"dependencies": dependencies, "testing": testing, "concurrency": concurrency,
         "persistence": persistence, "ci": ci, "packaging": packaging}
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=[*CASES, "all"])
    selection = parser.parse_args().case
    metrics = {name: run() for name, run in CASES.items() if selection in (name, "all")}
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
