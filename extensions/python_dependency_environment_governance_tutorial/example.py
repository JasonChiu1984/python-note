"""解析 requirements 檔，找出未固定版本、未附雜湊與重複宣告的相依套件（標準函式庫）。"""
import re

REQS = """\
pymodbus==3.16.2 --hash=sha256:aa11
requests>=2.31
pandas
fastapi==0.165.0
# 開發用
pytest==9.2.0 --hash=sha256:bb22
Requests==2.34.2 --hash=sha256:cc33
-e git+https://example.com/internal/bmslib.git#egg=bmslib
"""

LINE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)\s*(?P<spec>[<>=!~].*?)?\s*(?P<hash>--hash=\S+)?\s*$")


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()          # PEP 503 名稱正規化


def audit(text):
    seen, findings = {}, []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-e ") or "git+" in line:
            findings.append((n, line[:40], "可編輯／VCS 相依：無法重現，改用已發布的版本"))
            continue
        m = LINE.match(line)
        name = normalize(m["name"])
        if name in seen:
            findings.append((n, m["name"], f"與第 {seen[name]} 行重複（名稱正規化後相同）"))
        seen[name] = n
        if not m["spec"] or not m["spec"].startswith("=="):
            findings.append((n, m["name"], "未固定版本（應使用 == 或鎖定檔）"))
        if not m["hash"]:
            findings.append((n, m["name"], "未附雜湊，無法確認下載內容"))
    return findings


if __name__ == "__main__":
    for n, name, msg in audit(REQS):
        print(f"第 {n} 行 {name}: {msg}")
