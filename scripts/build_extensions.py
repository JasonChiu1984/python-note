"""Build the "延伸學習" (extension) section of each tutorial page.

Each page with a directory ``extensions/<page-stem>/`` gets a generated section
inserted just before ``</main>`` (or ``</body>``), between the markers
``<!-- extension:start -->`` and ``<!-- extension:end -->``.

Directory contents:
  meta.json   lang, case, updates, exercises (see README in extensions/)
  example.py  standard-library example; its real stdout becomes "預期輸出"

Usage:
  python scripts/build_extensions.py           # rebuild all pages
  python scripts/build_extensions.py --check   # fail if any page is out of date
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions"
START, END = "<!-- extension:start -->", "<!-- extension:end -->"

TEXT = {
    "zh": dict(title="延伸學習：實作、現場案例與自我檢查", example="可實跑範例", run="執行方式",
               output="預期輸出（以 Python {ver} 實際執行產生）", case="工程現場案例",
               updates="版本與法規更新（核對日期 {date}）", source="來源", exercises="練習題與自我檢查",
               answer="看解答", download="下載範例"),
    "en": dict(title="Further practice: runnable example, field case and self-check", example="Runnable example",
               run="How to run", output="Expected output (captured from a real run on Python {ver})",
               case="Field case", updates="Version and regulation updates (checked {date})", source="Source",
               exercises="Exercises and self-check", answer="Show answer", download="Download example"),
}
STYLE = (
    "<style>.ext-section{margin:2.5rem 0;padding:1.5rem;border:1px solid rgba(127,127,127,.35);border-radius:12px}"
    ".ext-section h3{margin-top:1.5rem}.ext-section details{margin:.5rem 0;padding:.5rem .75rem;"
    "border:1px solid rgba(127,127,127,.3);border-radius:8px}.ext-section summary{cursor:pointer;font-weight:600}"
    ".ext-section pre{overflow:auto;max-width:100%}.ext-section .ext-note{opacity:.85;font-size:.95em}</style>"
)


def missing_requirements(meta: dict) -> list[str]:
    import importlib.util
    return [m for m in meta.get("requires", []) if importlib.util.find_spec(m) is None]


def interpreter_for(meta: dict) -> str | None:
    """Pick the interpreter: the current one, or EXT_PYTHON_3XX from the environment for newer minimums."""
    import os
    need = tuple(meta.get("min_python", (3, 10)))
    if sys.version_info[:2] >= need:
        return sys.executable
    return os.environ.get(f"EXT_PYTHON_{need[0]}{need[1]}")


def python_version(exe: str) -> str:
    return subprocess.run([exe, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                          capture_output=True, text=True, check=True).stdout.strip()


def run_example(path: Path, exe: str = sys.executable) -> str:
    """Run twice with different hash seeds; the published output must not depend on either."""
    import os
    outputs = []
    for seed in ("0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([exe, "-X", "utf8", str(path)], cwd=tmp, capture_output=True,
                                  text=True, encoding="utf-8", timeout=120, env=env)
        if proc.returncode != 0:
            raise SystemExit(f"{path} failed:\n{proc.stderr}")
        outputs.append(proc.stdout.rstrip("\n"))
    if outputs[0] != outputs[1]:
        raise SystemExit(f"{path} output is not deterministic")
    return outputs[0]


def render(stem: str, page: Path) -> str:
    folder = EXT / stem
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    t = TEXT[meta.get("lang", "zh")]
    example = folder / "example.py"
    rel = Path("extensions") / stem / "example.py"
    href = Path(*[".."] * (len(page.relative_to(ROOT).parts) - 1), rel).as_posix()
    exe = interpreter_for(meta)
    ver = python_version(exe)
    parts = [STYLE, f'<section class="ext-section" id="extension"><h2>{t["title"]}</h2>']
    if meta.get("intro"):
        parts.append(f"<p>{meta['intro']}</p>")
    if example.exists():
        code = example.read_text(encoding="utf-8")
        out = run_example(example, exe)
        parts += [f'<h3>{t["example"]}：{meta["example_title"]}</h3>',
                  f"<p>{meta.get('example_desc', '')}</p>",
                  f'<p><a class="button" download href="{href}">{t["download"]} {html.escape(rel.name)}</a></p>',
                  f"<pre><code class=\"language-python\">{html.escape(code)}</code></pre>",
                  f'<p class="ext-note">{t["run"]}：<code>python example.py</code>'
                  f'{("，" if meta.get("lang","zh")=="zh" else ", ") + meta["run_note"] if meta.get("run_note") else ""}</p>',
                  f'<h4>{t["output"].format(ver=ver)}</h4><pre><code>{html.escape(out)}</code></pre>']
    if meta.get("case"):
        parts.append(f'<h3>{t["case"]}：{meta["case"]["title"]}</h3>')
        parts += [f"<p>{p}</p>" for p in meta["case"]["paragraphs"]]
        if meta["case"].get("steps"):
            parts.append("<ol>" + "".join(f"<li>{s}</li>" for s in meta["case"]["steps"]) + "</ol>")
    if meta.get("updates"):
        parts.append(f'<h3>{t["updates"].format(date=meta["checked"])}</h3><ul>')
        for u in meta["updates"]:
            src = "".join(f' <a href="{html.escape(s["url"])}">{t["source"]}：{s["title"]}</a>'
                          for s in u.get("sources", []))
            parts.append(f"<li>{u['text']}{src}</li>")
        parts.append("</ul>")
    if meta.get("exercises"):
        parts.append(f'<h3>{t["exercises"]}</h3><ol>')
        for ex in meta["exercises"]:
            parts.append(f"<li><p>{ex['q']}</p><details><summary>{t['answer']}</summary>{ex['a']}</details></li>")
        parts.append("</ol>")
    parts.append("</section>")
    return START + "".join(parts) + END


def apply(page: Path, block: str) -> str:
    text = page.read_text(encoding="utf-8")
    if START in text:
        head, rest = text.split(START, 1)
        _, tail = rest.split(END, 1)
        return head + block + tail
    anchor = "</main>" if "</main>" in text else "</body>"
    idx = text.rfind(anchor)
    return text[:idx] + block + "\n" + text[idx:]


def pages() -> dict[str, Path]:
    found = {}
    for p in [*ROOT.glob("*.html"), *ROOT.glob("python-3*-learning-kit/*.html"), *ROOT.glob("PythonReleaseNote/*.html")]:
        stem = p.relative_to(ROOT).with_suffix("").as_posix().replace("/", "__")
        found[stem] = p
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("only", nargs="*")
    args = ap.parse_args()
    known = pages()
    stale = []
    for folder in sorted(d for d in EXT.iterdir() if d.is_dir()):
        if args.only and folder.name not in args.only:
            continue
        page = known.get(folder.name)
        if page is None:
            raise SystemExit(f"no page for extensions/{folder.name}")
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        missing = missing_requirements(meta)
        if missing or interpreter_for(meta) is None:
            print(f"skip {folder.name}: missing {', '.join(missing) or 'Python ' + '.'.join(map(str, meta['min_python']))}")
            continue
        new = apply(page, render(folder.name, page))
        if new != page.read_text(encoding="utf-8"):
            stale.append(page.relative_to(ROOT).as_posix())
            if not args.check:
                page.write_text(new, encoding="utf-8")
    if args.check and stale:
        print("out of date:", *stale, sep="\n  ")
        return 1
    print(("checked" if args.check else "built"), "extensions;", len(stale), "page(s)", "stale" if args.check else "updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
