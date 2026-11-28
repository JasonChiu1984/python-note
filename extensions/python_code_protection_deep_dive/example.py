"""發行檔完整性清單：產生 SHA-256 清單、用 HMAC 簽署清單，安裝前逐檔驗證（標準函式庫）。

真實發行應使用非對稱簽章（例如 Ed25519 或 Sigstore），讓驗證端只持有公開金鑰；
本例為了只用標準函式庫改用 HMAC，示範的是「清單＋逐檔雜湊」的流程。
"""
import hashlib
import hmac
import json
import tempfile
from pathlib import Path

SIGNING_KEY = b"\x42" * 32


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: Path) -> dict:
    files = {p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}
    body = json.dumps(files, sort_keys=True).encode()
    return {"files": files, "sig": hmac.new(SIGNING_KEY, body, hashlib.sha256).hexdigest()}


def verify(root: Path, manifest: dict) -> list[str]:
    body = json.dumps(manifest["files"], sort_keys=True).encode()
    if not hmac.compare_digest(hmac.new(SIGNING_KEY, body, hashlib.sha256).hexdigest(), manifest["sig"]):
        return ["清單簽章錯誤：清單本身被修改"]
    problems = []
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    for name, digest in manifest["files"].items():
        if name not in actual:
            problems.append(f"缺少檔案：{name}")
        elif sha256(root / name) != digest:
            problems.append(f"內容不符：{name}")
    problems += [f"多出未列管檔案：{n}" for n in sorted(actual - manifest["files"].keys())]
    return problems


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "gateway-2.4.1"
        (root / "app").mkdir(parents=True)
        (root / "app" / "main.py").write_text("print('gateway')\n")
        (root / "app" / "points.json").write_text('{"SAT": {"addr": 0, "scale": 0.1}}\n')
        (root / "README.txt").write_text("v2.4.1\n")
        manifest = build_manifest(root)
        for name, digest in manifest["files"].items():
            print(f"{digest[:16]}…  {name}")
        print("原始發行檔：", verify(root, manifest) or "全部通過")
        (root / "app" / "points.json").write_text('{"SAT": {"addr": 0, "scale": 1.0}}\n')
        (root / "app" / "debug_shell.py").write_text("import os\n")
        print("被修改後：")
        for p in verify(root, manifest):
            print("  -", p)
        manifest["files"]["app/points.json"] = sha256(root / "app" / "points.json")
        print("攻擊者同步改清單：", verify(root, manifest))
