"""Offline synthetic release verification; Python 3.10+ and OpenSSL 3.x."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

def ssl(*args: str, verify_only: bool = False) -> bytes:
    result = subprocess.run(["openssl", *args], check=False, capture_output=True, timeout=10)
    if result.returncode:
        if verify_only:
            raise ValueError("驗章失敗：拒絕發布資料")
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout

def verify(root: Path, pinned_key: Path, floor: int, expected_product: str) -> bytes:
    # Verify the exact bytes held in memory; do not parse until verified.
    manifest = (root / "manifest.json").read_bytes()
    signature = (root / "manifest.sig").read_bytes()
    with TemporaryDirectory() as tmp:
        data, sig = (Path(tmp) / name for name in ("manifest", "signature"))
        data.write_bytes(manifest)
        sig.write_bytes(signature)
        ssl("pkeyutl", "-verify", "-pubin", "-inkey", str(pinned_key), "-rawin",
            "-in", str(data), "-sigfile", str(sig), verify_only=True)
    meta = json.loads(manifest)
    if (meta["product"] != expected_product or meta["file"] != "example.bin"
            or type(meta["version"]) is not int or meta["version"] < floor):
        raise ValueError("發行目標或版本不符：拒絕發布資料")
    payload = (root / "example.bin").read_bytes()
    if hashlib.sha256(payload).hexdigest() != meta["sha256"]:
        raise ValueError("檔案雜湊不符：拒絕發布資料")
    return payload  # In production install precisely these verified bytes, not a reopened file.

def demo() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        publisher, client, release = (root / name for name in ("publisher", "client", "release"))
        for folder in (publisher, client, release):
            folder.mkdir()
        private, pinned = publisher / "key.pem", client / "trusted.pem"
        ssl("genpkey", "-algorithm", "ED25519", "-out", str(private))
        ssl("pkey", "-in", str(private), "-pubout", "-out", str(pinned))
        payload = release / "example.bin"
        payload.write_bytes(b"synthetic release example\n")
        manifest, sig = release / "manifest.json", release / "manifest.sig"
        meta = {"product": "tutorial", "file": "example.bin", "version": 2,
                "sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}
        manifest.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")
        ssl("pkeyutl", "-sign", "-inkey", str(private), "-rawin", "-in", str(manifest), "-out", str(sig))
        assert verify(release, pinned, 2, "tutorial") == payload.read_bytes()
        print("PASS: 正常發行物通過驗章、版本與雜湊")

        def rejects(floor: int, expected: str) -> None:
            try:
                verify(release, pinned, floor, "tutorial")
            except ValueError as exc:
                if expected not in str(exc):
                    raise
                print("PASS:", str(exc))
                return
            raise AssertionError("錯誤檔案被接受")

        rejects(3, "版本不符")
        payload.write_bytes(b"edited release example\n")
        rejects(2, "雜湊不符")
        payload.write_bytes(b"synthetic release example\n")
        manifest.write_text(json.dumps({**meta, "version": 3}), encoding="utf-8")
        rejects(2, "驗章失敗")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    demo()
