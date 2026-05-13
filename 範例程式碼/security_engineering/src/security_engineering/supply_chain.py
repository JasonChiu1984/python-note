from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyRecord:
    name: str
    version: str
    hash: str


def validate_manifest(records: list[DependencyRecord]) -> dict[str, object]:
    missing = [item.name for item in records if not item.version or not item.hash.startswith("sha256:")]
    return {
        "dependencies_total": len(records),
        "passed": not missing,
        "missing_or_invalid": missing,
    }
