from __future__ import annotations

import hashlib
import json
import re
import tarfile
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class ReleaseGateError(RuntimeError):
    """Raised when release evidence is incomplete or inconsistent."""


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    version: str
    package: str
    changelog: Path
    dist_dir: Path

    @property
    def archive_name(self) -> str:
        return f"{self.name}-{self.version}.tar.gz"


def load_project_metadata(project_root: Path) -> ProjectMetadata:
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        raise ReleaseGateError("Missing pyproject.toml")

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})
    tool = data.get("tool", {}).get("release_gate", {})
    name = project.get("name")
    version = project.get("version")
    package = tool.get("package") or str(name).replace("-", "_")
    changelog = project_root / tool.get("changelog", "CHANGELOG.md")
    dist_dir = project_root / tool.get("dist_dir", "dist")

    if not name or not version:
        raise ReleaseGateError("pyproject.toml must define project.name and project.version")
    return ProjectMetadata(name=name, version=version, package=package, changelog=changelog, dist_dir=dist_dir)


def read_package_version(project_root: Path, package: str) -> str:
    init_file = project_root / "src" / package / "__init__.py"
    if not init_file.exists():
        raise ReleaseGateError(f"Missing package init: {init_file}")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_file.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ReleaseGateError(f"Missing __version__ in {init_file}")
    return match.group(1)


def validate_release_metadata(project_root: Path) -> ProjectMetadata:
    metadata = load_project_metadata(project_root)
    package_version = read_package_version(project_root, metadata.package)
    if package_version != metadata.version:
        raise ReleaseGateError(f"Version mismatch: pyproject={metadata.version}, package={package_version}")
    if not metadata.changelog.exists():
        raise ReleaseGateError(f"Missing changelog: {metadata.changelog}")
    changelog_text = metadata.changelog.read_text(encoding="utf-8")
    if f"## v{metadata.version}" not in changelog_text:
        raise ReleaseGateError(f"Missing changelog entry for v{metadata.version}")
    return metadata


def iter_release_files(project_root: Path) -> Iterable[Path]:
    include_roots = [project_root / "pyproject.toml", project_root / "README.md", project_root / "CHANGELOG.md", project_root / "src"]
    for root in include_roots:
        if root.is_file():
            yield root
        elif root.is_dir():
            for path in sorted(root.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                    yield path


def build_source_archive(project_root: Path, dist_dir: Path | None = None) -> Path:
    metadata = validate_release_metadata(project_root)
    target_dir = dist_dir or metadata.dist_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / metadata.archive_name
    prefix = f"{metadata.name}-{metadata.version}"

    with tarfile.open(archive_path, "w:gz") as archive:
        for path in iter_release_files(project_root):
            relative = path.relative_to(project_root)
            tar_info = archive.gettarinfo(str(path), arcname=str(Path(prefix) / relative))
            tar_info.uid = tar_info.gid = 0
            tar_info.uname = tar_info.gname = ""
            tar_info.mtime = 0
            with path.open("rb") as source:
                archive.addfile(tar_info, source)
    return archive_path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 64), b""):
            digest.update(block)
    return digest.hexdigest()


def write_release_manifest(project_root: Path, archive_path: Path) -> Path:
    metadata = validate_release_metadata(project_root)
    manifest = {
        "name": metadata.name,
        "version": metadata.version,
        "package": metadata.package,
        "artifact": archive_path.name,
        "sha256": sha256_file(archive_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [str(path.relative_to(project_root)) for path in iter_release_files(project_root)],
        "gates": ["metadata", "version", "changelog", "archive", "checksum"],
    }
    manifest_path = archive_path.with_name("release-manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def run_release_gate(project_root: Path, dist_dir: Path | None = None) -> tuple[Path, Path]:
    archive_path = build_source_archive(project_root, dist_dir=dist_dir)
    manifest_path = write_release_manifest(project_root, archive_path)
    return archive_path, manifest_path
