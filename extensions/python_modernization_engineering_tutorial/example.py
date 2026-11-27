"""用 ast 掃描程式碼中已移除或已棄用的標準函式庫用法，作為升級 Python 版本前的檢查（標準函式庫）。"""
import ast

REMOVED = {           # 模組: (移除版本, 替代方案)
    "distutils": ("3.12", "setuptools 或 packaging"),
    "imp": ("3.12", "importlib"),
    "asyncore": ("3.12", "asyncio"),
    "asynchat": ("3.12", "asyncio"),
    "cgi": ("3.13", "email.message 或 multipart 套件"),
    "telnetlib": ("3.13", "第三方套件（如 telnetlib3）"),
    "pipes": ("3.13", "subprocess、shlex.quote"),
}
DEPRECATED_CALLS = {
    ("datetime", "utcnow"): ("3.12 起棄用", "datetime.now(timezone.utc)"),
    ("datetime", "utcfromtimestamp"): ("3.12 起棄用", "datetime.fromtimestamp(ts, timezone.utc)"),
}

SOURCE = '''
import telnetlib
from distutils.version import LooseVersion
from datetime import datetime, timezone

def stamp():
    return datetime.utcnow().isoformat()

def ok():
    return datetime.now(timezone.utc)
'''


def scan(src, filename="legacy_gateway.py"):
    tree = ast.parse(src, filename)
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module.split(".")[0]]
        for m in mods:
            if m in REMOVED:
                ver, alt = REMOVED[m]
                yield node.lineno, f"{m} 已於 Python {ver} 移除 → {alt}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            key = (base.id if isinstance(base, ast.Name) else None, node.func.attr)
            if key in DEPRECATED_CALLS:
                when, alt = DEPRECATED_CALLS[key]
                yield node.lineno, f"{key[0]}.{key[1]}() {when} → {alt}"


if __name__ == "__main__":
    for line, msg in sorted(scan(SOURCE)):
        print(f"legacy_gateway.py:{line}: {msg}")
