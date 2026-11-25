"""Python 3.11+。離線檢查選定的合成 wheel；不安裝、不匯入 wheel、不解析完整鎖檔。"""
import argparse
import base64
import csv
from email.parser import BytesParser
from hashlib import sha256
from io import StringIO
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from zipfile import ZIP_STORED, ZipFile, ZipInfo

NAME = "contract_demo"
VERSION = "1.0.0"
TAG = "py3-none-any"
FILENAME = f"{NAME}-{VERSION}-{TAG}.whl"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"
REQUIRES_PYTHON = ">=3.11"
MAX_WHEEL_BYTES = 1_048_576
MAX_METADATA_BYTES = 4096


class ContractError(ValueError):
    """檢查不通過；不建議將錯誤當成可忽略的警告。"""


def build_wheel(directory):
    """建立有 METADATA、WHEEL 與 RECORD 的小型合成 wheel，位元組可重現。"""
    files = {
        f"{NAME}/__init__.py": b'__version__ = "1.0.0"\n',
        f"{DIST_INFO}/METADATA": (
            f"Metadata-Version: 2.1\nName: {NAME}\nVersion: {VERSION}\n"
            f"Requires-Python: {REQUIRES_PYTHON}\n\n"
        ).encode(),
        f"{DIST_INFO}/WHEEL": (
            f"Wheel-Version: 1.0\nGenerator: contract-lab\n"
            f"Root-Is-Purelib: true\nTag: {TAG}\n\n"
        ).encode(),
    }
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for key, value in sorted(files.items()):
        digest = base64.urlsafe_b64encode(sha256(value).digest()).rstrip(b"=").decode()
        writer.writerow((key, "sha256=" + digest, len(value)))
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    files[f"{DIST_INFO}/RECORD"] = output.getvalue().encode()
    path = directory / FILENAME
    with ZipFile(path, "w", compression=ZIP_STORED) as archive:
        for key, value in sorted(files.items()):
            entry = ZipInfo(key, date_time=(2024, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, value)
    return path


def write_contract(path):
    """教學才臨時建立基準。實務上契約及 SHA-256 須由獨立可信來源發布。"""
    contract = path.parent / "contract.toml"
    contract.write_text(
        f'[wheel]\nfilename = "{FILENAME}"\nname = "{NAME}"\n'
        f'version = "{VERSION}"\ntag = "{TAG}"\n'
        f'requires_python = "{REQUIRES_PYTHON}"\n'
        f'sha256 = "{sha256(path.read_bytes()).hexdigest()}"\n',
        encoding="utf-8",
    )
    return contract


def inspect_wheel(path, contract_path, runtime):
    """只支援本例一個 universal tag 與單一 >=major.minor Python 門檻。"""
    with contract_path.open("rb") as handle:
        rule = tomllib.load(handle)["wheel"]
    if rule["filename"] != path.name:
        raise ContractError("wheel 檔名不符")
    name, version, tag = rule["name"], rule["version"], rule["tag"]
    if path.name != f"{name}-{version}-{tag}.whl":
        raise ContractError("契約名稱、版本、標籤與檔名矛盾")
    if tag != TAG:
        raise ContractError(f"標籤不支援：此 lab 只檢查 {TAG}")
    if path.stat().st_size > MAX_WHEEL_BYTES:
        raise ContractError("超過此小型 lab 的 wheel 大小上限")
    digest = sha256(path.read_bytes()).hexdigest()
    if digest != rule["sha256"]:
        raise ContractError("SHA-256 不符：不使用漂移的成品")

    def metadata(archive, kind):
        key = f"{name}-{version}.dist-info/{kind}"
        matches = [m for m in archive.infolist() if m.filename == key]
        if len(matches) != 1 or matches[0].file_size > MAX_METADATA_BYTES:
            raise ContractError(f"{kind} 缺漏、重名或過大")
        return BytesParser().parsebytes(archive.read(matches[0]))

    with ZipFile(path) as archive:
        info = metadata(archive, "METADATA")
        attrs = metadata(archive, "WHEEL")
        if attrs.get_all("Tag") != [tag]:
            raise ContractError("內嵌 wheel 標籤與契約不符")
        if info.get_all("Name") != [name] or info.get_all("Version") != [version]:
            raise ContractError("內嵌套件名稱或版本與契約不符")
        if info.get_all("Requires-Dist"):
            raise ContractError("本例不解析傳遞依賴，有 Requires-Dist 就不通過")
        actual = info.get_all("Requires-Python")
        if actual != [rule["requires_python"]]:
            raise ContractError("內嵌 Python 門檻與契約不符")
    match = re.fullmatch(r">=([0-9]+)\.([0-9]+)", actual[0])
    if not match:
        raise ContractError("此 lab 只示範單一 >=major.minor 門檻")
    if tuple(runtime[:2]) < tuple(map(int, match.groups())):
        raise ContractError("Python 執行環境低於 Requires-Python")
    return digest


def demo():
    """建立並驗證兩種失敗；環境門檻失敗使用合成 Python 3.10 版本資訊。"""
    with TemporaryDirectory(prefix="py-contract-") as tmp:
        wheel = build_wheel(Path(tmp))
        manifest = write_contract(wheel)
        digest = inspect_wheel(wheel, manifest, sys.version_info[:2])
        print(f"PASS 合成 wheel：{wheel.name}（{wheel.stat().st_size} bytes）")
        print(f"PASS SHA-256：{digest}")
        print(f"PASS Python {sys.version_info.major}.{sys.version_info.minor}：{REQUIRES_PYTHON}；{TAG}；直接依賴 0")
        for runtime, drift in (((3, 10), False), (sys.version_info[:2], True)):
            if drift:
                contents = bytearray(wheel.read_bytes())
                contents[-1] ^= 1
                wheel.write_bytes(contents)
            try:
                inspect_wheel(wheel, manifest, runtime)
            except ContractError as err:
                print(f"EXPECTED REJECT：{err}")
            else:
                raise RuntimeError("預期應拒絕，卻通過")
        print("完成：未安裝、不連網；暫存目錄自動清除。")


class TestContract(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.wheel = build_wheel(self.directory)
        self.contract = write_contract(self.wheel)

    def test_valid_and_reproducible(self):
        first = self.wheel.read_bytes()
        self.assertEqual(build_wheel(self.directory).read_bytes(), first)
        self.assertEqual(inspect_wheel(self.wheel, self.contract, (3, 11)), sha256(first).hexdigest())

    def test_hash_drift(self):
        data = bytearray(self.wheel.read_bytes())
        data[-1] ^= 1
        self.wheel.write_bytes(data)
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            inspect_wheel(self.wheel, self.contract, (3, 11))

    def test_python_gate(self):
        with self.assertRaisesRegex(ContractError, "Requires-Python"):
            inspect_wheel(self.wheel, self.contract, (3, 10))

    def test_unsupported_platform_tag(self):
        substitute = "cp311-cp311-win_amd64"
        new = self.wheel.with_name(self.wheel.name.replace(TAG, substitute))
        self.wheel.rename(new)
        self.contract.write_text(self.contract.read_text().replace(TAG, substitute))
        with self.assertRaisesRegex(ContractError, "標籤不支援"):
            inspect_wheel(new, self.contract, (3, 11))

    def test_metadata_contract_mismatch(self):
        self.contract.write_text(self.contract.read_text().replace(">=3.11", ">=3.10"))
        with self.assertRaisesRegex(ContractError, "內嵌 Python"):
            inspect_wheel(self.wheel, self.contract, (3, 11))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="僅接受合成資料；不能取代 pip 的依賴解析或平台相容性檢查。",
    )
    parser.add_argument("action", nargs="?", choices=["demo"], help="執行合成 wheel 的成功與失敗路徑")
    parser.add_argument("--self-test", action="store_true", help="執行 5 個離線單元測試")
    args = parser.parse_args(argv)
    if args.self_test and args.action:
        parser.error("請擇一使用 demo 或 --self-test")
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestContract))
        return 0 if result.wasSuccessful() else 1
    if args.action == "demo":
        demo()
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
