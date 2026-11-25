"""Local manifest gate. Validates evidence metadata; does not run scans or deploy."""

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = (
    "tests", "lint_and_types", "dependency_audit", "secret_scan", "sbom",
    "artifact_smoke", "rollback_rehearsal",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def distinct_keys(pairs: list[tuple]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key: {key}")
        out[key] = value
    return out


def run(candidate: Path, manifest: Path) -> list[str]:
    digest = sha256(candidate)
    payload = json.loads(manifest.read_text(encoding="utf-8"),
                         object_pairs_hook=distinct_keys)
    if not isinstance(payload, dict) or payload.get("candidate_sha256") != digest:
        return ["candidate digest mismatch"]
    gates = payload.get("gates")
    if not isinstance(gates, dict):
        return ["invalid gates"]
    errors = []
    for name in REQUIRED:
        item = gates.get(name)
        if (not isinstance(item, dict) or item.get("status") != "pass"
                or not isinstance(item.get("evidence"), str)
                or not item["evidence"].strip()):
            errors.append(f"missing passing evidence: {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        errors = run(args.candidate, args.manifest)
    except (ValueError, OSError):
        print(json.dumps({"decision": "BLOCK", "reasons": ["unreadable artifact or manifest"]}))
        return 2
    print(json.dumps({"decision": "BLOCK" if errors else "PASS", "reasons": errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
