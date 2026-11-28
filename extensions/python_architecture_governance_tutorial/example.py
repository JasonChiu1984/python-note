"""用 ast 檢查分層架構的 import 規則：domain 不可依賴 adapters 或 app（標準函式庫）。"""
import ast

ALLOWED = {                 # 層: 可以匯入的層
    "domain": set(),
    "services": {"domain"},
    "adapters": {"domain", "services"},
    "app": {"domain", "services", "adapters"},
}

FILES = {
    "bms/domain/point.py": "from dataclasses import dataclass\n",
    "bms/domain/alarm.py": "from bms.adapters.modbus import read_register\n",
    "bms/services/report.py": "from bms.domain.point import Point\nimport bms.app.cli\n",
    "bms/adapters/modbus.py": "from bms.domain.point import Point\n",
    "bms/app/cli.py": "from bms.services.report import build\n",
}


def layer_of(module):
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "bms" else None


def violations():
    for path, src in sorted(FILES.items()):
        here = path.split("/")[1]
        for node in ast.walk(ast.parse(src, path)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                target = layer_of(m)
                if target and target != here and target not in ALLOWED[here]:
                    yield f"{path}:{node.lineno} {here} 不可匯入 {target}（{m}）"


if __name__ == "__main__":
    found = list(violations())
    for v in found:
        print(v)
    print(f"共 {len(found)} 個違規；CI 中應以非零結束碼失敗" if found else "沒有違規")
