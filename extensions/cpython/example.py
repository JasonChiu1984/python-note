"""用標準函式庫 zipapp 把小工具打包成單一 .pyz，並驗證可直接執行（標準函式庫）。

zipapp 不包含直譯器，目標機器仍需安裝相容版本的 Python；需要完全獨立的執行檔時才考慮 PyInstaller 等工具。
"""
import subprocess
import sys
import tempfile
import zipapp
import zipfile
from pathlib import Path

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "pointcheck"
        (src / "pointcheck").mkdir(parents=True)
        (src / "pointcheck" / "__init__.py").write_text("")
        (src / "pointcheck" / "cli.py").write_text(
            "import sys\n"
            "def main():\n"
            "    addrs = [int(a) for a in sys.argv[1:]]\n"
            "    bad = [a for a in addrs if not 0 <= a <= 65535]\n"
            "    print('檢查', len(addrs), '個位址，超出範圍：', bad or '無')\n"
            "    sys.exit(1 if bad else 0)   # zipapp 產生的 __main__ 不會把回傳值當結束碼\n")
        target = Path(tmp) / "pointcheck.pyz"
        zipapp.create_archive(src, target, interpreter="/usr/bin/env python3",
                              main="pointcheck.cli:main", compressed=True)
        with zipfile.ZipFile(target) as z:
            print("封裝內容：", sorted(n for n in z.namelist() if not n.endswith("/")))
        print("檔案開頭（shebang）：", target.read_bytes().split(b"\n", 1)[0].decode())
        for args in (["0", "40001", "65535"], ["70000", "12"]):
            r = subprocess.run([sys.executable, str(target), *args], capture_output=True, text=True)
            print(f"執行 {args} → 結束碼 {r.returncode}；{r.stdout.strip()}")
