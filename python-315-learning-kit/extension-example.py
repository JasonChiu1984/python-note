"""Python 3.15 升級前檢查：逐項確認本機直譯器是否具備 3.15 新功能，並提示 3.14 以前的替代寫法（需 Python 3.10+；在 3.15 上全部為可用）。"""
import asyncio
import builtins
import re
import sys
import typing

CHECKS = [
    ("frozendict（PEP 814）", lambda: hasattr(builtins, "frozendict"), "types.MappingProxyType（唯讀但不可雜湊）"),
    ("內建 sentinel", lambda: hasattr(builtins, "sentinel"), "模組層級 object() 加自訂 __repr__"),
    ("推導式解包（PEP 798）", lambda: _compiles("[*x for x in [[1]]]"), "[y for x in xs for y in x]"),
    ("lazy import（PEP 810）", lambda: _compiles("lazy import json"), "函式內匯入或 importlib.util.LazyLoader"),
    ("re.prefixmatch()", lambda: hasattr(re, "prefixmatch"), "re.match()"),
    ("TaskGroup.cancel()", lambda: hasattr(asyncio.TaskGroup, "cancel") if hasattr(asyncio, "TaskGroup") else False,
     "自訂例外觸發 TaskGroup 取消"),
    ("typing.disjoint_base（PEP 800）", lambda: hasattr(typing, "disjoint_base"), "以註解說明，不做型別檢查"),
    ("預設 UTF-8 模式（PEP 686）", lambda: sys.flags.utf8_mode == 1, "PYTHONUTF8=1 或 open(..., encoding='utf-8')"),
]


def _compiles(src):
    try:
        compile(src, "<check>", "exec")
        return True
    except SyntaxError:
        return False


if __name__ == "__main__":
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    for name, check, fallback in CHECKS:
        ok = check()
        print(f"  {'✔' if ok else '✘'} {name:<30} {'' if ok else '替代：' + fallback}")
