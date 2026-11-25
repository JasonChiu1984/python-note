"""Verify the lab's exact package pair; then smoke-test the wheel in a clean venv."""

import argparse
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import venv

NAMES = ("release_note_lab-0.1.0-py3-none-any.whl", "release_note_lab-0.1.0.tar.gz")
MANIFEST = "SHA256SUMS"


def manifest_bytes(dist: Path) -> bytes:
    actual = {p.name for p in dist.iterdir() if p.name != MANIFEST}
    if actual != set(NAMES):
        raise SystemExit(f"Expected only the two lab artifacts; found {sorted(actual)}")
    lines = []
    for name in NAMES:
        with (dist / name).open("rb") as artifact:
            sha = hashlib.sha256()
            while block := artifact.read(1024 * 1024):
                sha.update(block)
        lines.append(f"{sha.hexdigest()}  {name}\n")
    return "".join(lines).encode("ascii")


def verify(dist: Path) -> None:
    if not hmac.compare_digest((dist / MANIFEST).read_bytes(), manifest_bytes(dist)):
        raise SystemExit("SHA-256 mismatch: do not install or promote these files")


def smoke(dist: Path) -> None:
    with TemporaryDirectory(prefix="release-smoke-") as temp:
        temp = Path(temp)
        envdir = temp / "venv"
        venv.EnvBuilder(with_pip=True).create(envdir)
        bindir = envdir / ("Scripts" if os.name == "nt" else "bin")
        py = bindir / ("python.exe" if os.name == "nt" else "python")
        exe = bindir / ("release-note-lab.exe" if os.name == "nt" else "release-note-lab")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "PIP_"))}
        subprocess.run(
            [py, "-I", "-m", "pip", "--isolated", "install", "--no-index",
             "--no-deps", dist / NAMES[0]],
            cwd=temp, env=env, check=True,
        )
        subprocess.run([py, "-I", "-m", "pip", "--isolated", "check"],
                       cwd=temp, env=env, check=True)
        actual = subprocess.check_output([exe], cwd=temp, env=env, text=True).strip()
        expected = "0.1.0: Release artifact verified"
        if actual != expected:
            raise SystemExit(f"CLI output mismatch: {actual!r}")
        print(f"{actual}; wheel smoke PASS ({sys.version.split()[0]})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    parser.add_argument("mode", choices=("write", "verify", "smoke"))
    args = parser.parse_args()
    dist = args.dist.resolve()
    if args.mode == "write":
        with (dist / MANIFEST).open("xb") as target:
            target.write(manifest_bytes(dist))
    else:
        verify(dist)
        print("SHA-256 PASS")
        if args.mode == "smoke":
            smoke(dist)


if __name__ == "__main__":
    main()
