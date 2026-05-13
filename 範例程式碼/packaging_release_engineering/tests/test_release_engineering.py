from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from packaging_release_engineering.release import (
    ReleaseGateError,
    build_source_archive,
    load_project_metadata,
    run_release_gate,
    validate_release_metadata,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseEngineeringTests(unittest.TestCase):
    def test_load_project_metadata(self) -> None:
        metadata = load_project_metadata(PROJECT_ROOT)
        self.assertEqual(metadata.name, "packaging-release-engineering")
        self.assertEqual(metadata.version, "0.1.0")
        self.assertEqual(metadata.package, "packaging_release_engineering")

    def test_validate_release_metadata(self) -> None:
        metadata = validate_release_metadata(PROJECT_ROOT)
        self.assertEqual(metadata.archive_name, "packaging-release-engineering-0.1.0.tar.gz")

    def test_detects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="release-mismatch-") as tmp:
            copied = Path(tmp) / "project"
            shutil.copytree(PROJECT_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "dist"))
            init_file = copied / "src" / "packaging_release_engineering" / "__init__.py"
            init_file.write_text('__version__ = "9.9.9"\n', encoding="utf-8")
            with self.assertRaisesRegex(ReleaseGateError, "Version mismatch"):
                validate_release_metadata(copied)

    def test_build_source_archive_excludes_generated_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="release-archive-") as tmp:
            dist = Path(tmp) / "dist"
            archive_path = build_source_archive(PROJECT_ROOT, dist_dir=dist)
            with tarfile.open(archive_path, "r:gz") as archive:
                names = archive.getnames()
            self.assertTrue(any(name.endswith("pyproject.toml") for name in names))
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertFalse(any(name.endswith(".pyc") for name in names))
            self.assertFalse(any("/dist/" in name for name in names))

    def test_run_release_gate_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="release-manifest-") as tmp:
            archive_path, manifest_path = run_release_gate(PROJECT_ROOT, dist_dir=Path(tmp))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact"], archive_path.name)
            self.assertEqual(len(manifest["sha256"]), 64)
            self.assertIn("metadata", manifest["gates"])
            self.assertIn("src/packaging_release_engineering/release.py", manifest["files"])


if __name__ == "__main__":
    unittest.main()
