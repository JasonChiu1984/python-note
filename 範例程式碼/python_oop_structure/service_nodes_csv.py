"""Parse the CSV exported by the OOP lab. Run with Python 3.11 or newer."""
from __future__ import annotations

import argparse
import builtins
import csv
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType


# On older interpreters an Enum member supplies identity, and a read-only
# mapping is enough for this exercise. The example never hashes the mapping.
class Missing(Enum):
    UNSET = "UNSET"


if hasattr(builtins, "sentinel"):
    UNSET = builtins.sentinel("UNSET")
    Port = int | UNSET
    freeze_tags = builtins.frozendict
else:
    UNSET = Missing.UNSET
    Port = int | Missing
    freeze_tags = MappingProxyType


@dataclass(frozen=True, slots=True)
class ServiceNode:
    name: str
    role: str
    port: Port
    tags: Mapping[str, str]

    @classmethod
    def from_row(cls, row: dict[str, str]) -> ServiceNode:
        name = row["name"].strip()
        if not name:
            raise ValueError("missing name")
        raw = row["port"].strip()
        if raw and not (raw.isascii() and raw.isdecimal() and 1 <= int(raw) <= 65535):
            raise ValueError(f"invalid port {raw!r}")
        tags = {}
        for part in row["tags"].split(";"):
            if part.strip():
                key, _, value = part.partition("=")
                tags[key.strip()] = value.strip() or "true"
        return cls(name, row["role"].strip() or "worker",
                   int(raw) if raw else UNSET, freeze_tags(tags))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", nargs="?", type=Path,
                        default=Path(__file__).with_name("service_nodes.csv"))
    args = parser.parse_args()
    counts = Counter()
    with args.csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["name", "role", "port", "tags"]:
            parser.error("expected header: name,role,port,tags")
        for row in reader:
            try:
                if None in row or None in row.values():
                    raise ValueError("expected four fields")
                node = ServiceNode.from_row(row)
            except ValueError as error:
                counts["error"] += 1
                print(f"line {reader.line_num}: {error}")
                continue
            status = "unset" if node.port is UNSET else "valid"
            counts[status] += 1
            print(node.name, node.role, "UNSET" if node.port is UNSET else node.port,
                  dict(node.tags))
    print(f"valid={counts['valid']} unset={counts['unset']} error={counts['error']}")


if __name__ == "__main__":
    main()
