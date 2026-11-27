"""Read-only Linux cgroup v2 collector; no daemon socket or third-party dependency."""
import argparse
import json
import os
import platform
import re
from pathlib import Path
from time import time_ns

SCALARS = ("cpu.max", "cpu.weight", "cpuset.cpus.effective", "memory.current",
           "memory.high", "memory.max", "memory.swap.max", "pids.current", "pids.max")
COUNTERS = {"cpu.stat": ("usage_usec", "nr_periods", "nr_throttled", "throttled_usec"),
            "memory.events.local": ("high", "max", "oom", "oom_kill", "oom_group_kill"),
            "pids.events": ("max",)}


def unescape(value):
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value)


def read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def locate(proc, pid):
    if not proc.is_dir():
        return None
    membership = read(proc / "cgroup") or ""
    rows = [row[3:] for row in membership.splitlines() if row.startswith("0::/")]
    if len(rows) != 1:
        return None
    group = Path(rows[0])
    for line in (read(proc / "mountinfo") or "").splitlines():
        lhs, sep, rhs = line.partition(" - ")
        parts = lhs.split()
        if not sep or len(parts) < 5 or rhs.split()[:1] != ["cgroup2"]:
            continue
        root, mount = map(lambda x: Path(unescape(x)), parts[3:5])
        options = [group.relative_to("/")]
        if group.is_relative_to(root):
            options.insert(0, group.relative_to(root))
        for relative in options:
            # Never walk up to an ancestor or trust namespace-relative paths alone.
            if ".." in relative.parts:
                continue
            path = mount / relative
            try:
                inode = path.stat()
            except OSError:
                continue
            procs = read(path / "cgroup.procs")
            if procs is not None and str(pid) in procs.split():
                return path, [inode.st_dev, inode.st_ino]
    return None


def parse_counters(raw, keys):
    found = {}
    for row in (raw or "").splitlines():
        items = row.split()
        if len(items) == 2 and items[1].isascii() and items[1].isdigit():
            found[items[0]] = int(items[1])
    return {key: found.get(key) for key in keys}


def snapshot():
    base = {"schema": 1, "kernel": platform.release(), "sample_unix_ns": time_ns(),
            "boot_id": read(Path("/proc/sys/kernel/random/boot_id"))}
    result = locate(Path("/proc/self"), os.getpid())
    if result is None:
        return dict(base, status="unavailable", reason="verified cgroup v2 leaf not readable")
    path, obj = result
    return dict(base, status="ok", identity=obj, scalars={k: read(path / k) for k in SCALARS},
                counters={f: parse_counters(read(path / f), keys) for f, keys in COUNTERS.items()})


def compare(a, b):
    if any(s.get("schema") != 1 or s.get("status") != "ok" or not s.get("boot_id") for s in (a, b)):
        raise ValueError("both samples must be readable v2 snapshots with boot identity")
    if (a["boot_id"], a["identity"]) != (b["boot_id"], b["identity"]):
        raise ValueError("samples belong to different cgroup instances")
    if a["sample_unix_ns"] >= b["sample_unix_ns"]:
        raise ValueError("sample order invalid; check clock or input")
    delta = {}
    for f, keys in COUNTERS.items():
        delta[f] = {}
        for k in keys:
            before = a["counters"].get(f, {}).get(k)
            after = b["counters"].get(f, {}).get(k)
            if before is not None and after is not None and after < before:
                raise ValueError(f"counter reset: {f}/{k}")
            delta[f][k] = None if before is None or after is None else after - before
    return {"schema": 1, "delta": delta,
            "configuration_changed": [k for k in SCALARS
              if not k.endswith(".current") and a["scalars"].get(k) != b["scalars"].get(k)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    args = parser.parse_args()
    try:
        result = compare(*(json.loads(path.read_text()) for path in args.diff)) if args.diff else snapshot()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if result.get("status") == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
