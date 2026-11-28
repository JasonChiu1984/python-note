"""交付前自動檢查專案結構契約：必要檔案、版本號一致、測試存在、沒有遺留秘密（標準函式庫）。"""
import re
import tempfile
from pathlib import Path

REQUIRED = ["README.md", "pyproject.toml", "CHANGELOG.md", "src/bmsreport/__init__.py", "tests/test_report.py"]
SECRET = re.compile(r"(password|passwd|api[_-]?key|token)\s*=\s*['\"][^'\"]{6,}", re.I)


def check(root: Path):
    problems = [f"缺少 {p}" for p in REQUIRED if not (root / p).exists()]
    pyproject = (root / "pyproject.toml").read_text() if (root / "pyproject.toml").exists() else ""
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    version = m.group(1) if m else None
    changelog = (root / "CHANGELOG.md").read_text() if (root / "CHANGELOG.md").exists() else ""
    if version and f"## {version}" not in changelog:
        problems.append(f"CHANGELOG 沒有 {version} 的條目")
    for p in root.rglob("*.py"):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if SECRET.search(line):
                problems.append(f"疑似寫死秘密：{p.relative_to(root)}:{i}")
    return version, problems


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src/bmsreport").mkdir(parents=True)
        (root / "README.md").write_text("# bmsreport\n")
        (root / "pyproject.toml").write_text('[project]\nname = "bmsreport"\nversion = "1.2.0"\n')
        (root / "CHANGELOG.md").write_text("## 1.1.0\n- 初版\n")
        (root / "src/bmsreport/__init__.py").write_text('DB_PASSWORD = "Bms#2026!"\n')
        version, problems = check(root)
        print(f"版本 {version}，發現 {len(problems)} 個問題：")
        for p in problems:
            print("  -", p)
        (root / "tests").mkdir()
        (root / "tests/test_report.py").write_text("def test_ok():\n    assert True\n")
        (root / "CHANGELOG.md").write_text("## 1.2.0\n- 新增月報\n## 1.1.0\n- 初版\n")
        (root / "src/bmsreport/__init__.py").write_text('import os\nDB_PASSWORD = os.environ["BMS_DB_PASSWORD"]\n')
        version, problems = check(root)
        print(f"修正後：{'可以交付' if not problems else problems}")
