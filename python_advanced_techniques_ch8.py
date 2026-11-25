"""Python 神乎其技：獨立執行各技巧，需 Python 3.11 以上。"""
import argparse
import subprocess
import sys
import tempfile

CASES = [('8-1', '用 dir() 與 help() 查詢物件能力', 'from contextlib import redirect_stdout\nfrom inspect import signature\nfrom io import StringIO\n\nassert "get" in dir({})\nout = StringIO()\nwith redirect_stdout(out):\n    help(dict.get)\nassert "get" in out.getvalue()\n\ndef normalize(value, scale=1.0):\n    return value * scale\n\nassert list(signature(normalize).parameters) == ["value", "scale"]\nassert normalize(12, scale=0.1) == 12 * 0.1\n'), ('8-2', '用 venv 建立不同 Python 版本的環境', 'import os\nimport subprocess\nimport sys\nimport tempfile\nimport venv\nfrom pathlib import Path\n\nwith tempfile.TemporaryDirectory() as tmp:\n    env = Path(tmp) / "demo"\n    venv.EnvBuilder(with_pip=False).create(env)\n    executable = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")\n    facts = subprocess.check_output([\n        str(executable), "-c",\n        "import sys; print(sys.version_info[:2]); print(sys.prefix != sys.base_prefix)"\n    ], text=True).splitlines()\n    assert facts == [str(tuple(sys.version_info[:2])), "True"]\n'), ('8-3', '用 dis 看 bytecode，但別硬綁指令名稱', 'import dis\nimport platform\n\ndef total(price, quantity):\n    return price * quantity + 2\n\ninstructions = list(dis.get_instructions(total))\nassert total(5, 3) == 17\nassert instructions and all(isinstance(op.opname, str) for op in instructions)\nassert total.__code__.co_argcount == 2\nprint(platform.python_implementation(), platform.python_version())\ndis.dis(total)  # 觀察此次版本的輸出，不把指令清單當契約。\n')]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="只跑一項，例如 2-1")
    args = parser.parse_args()
    selected = [row for row in CASES if args.case is None or row[0] == args.case]
    if not selected:
        parser.error("無此技巧編號")
    failures = 0
    for code_id, title, source in selected:
        # 各題分開解譯與工作目錄，避免全域名稱、暫存產物互相影響。
        with tempfile.TemporaryDirectory() as work:
            try:
                child = subprocess.run(
                    [sys.executable, "-I", "-X", "utf8", "-c", source],
                    cwd=work, capture_output=True, text=True, encoding="utf-8",
                    timeout=20,
                )
            except subprocess.TimeoutExpired:
                print(f"FAIL {code_id} {title}：逾時", flush=True)
                failures += 1
                continue
        print(f"{'PASS' if child.returncode == 0 else 'FAIL'} {code_id} {title}", flush=True)
        if child.returncode != 0:
            print(child.stdout + child.stderr, file=sys.stderr)
            failures += 1
    print(f"{len(selected) - failures}/{len(selected)} 通過")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
