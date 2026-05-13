from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from packaging_release_engineering.release import run_release_gate  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="release-gate-") as tmp:
        archive_path, manifest_path = run_release_gate(PROJECT_ROOT, dist_dir=Path(tmp))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert archive_path.exists(), "archive missing"
        assert len(manifest["sha256"]) == 64, "invalid sha256"
        assert "src/packaging_release_engineering/release.py" in manifest["files"], "release module missing"
    print("release smoke passed: metadata + archive + checksum + manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
