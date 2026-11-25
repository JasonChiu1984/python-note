"""Refresh source listings embedded in the HTML lessons. Use --check in CI."""
import argparse
from html import escape
from pathlib import Path
import re
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "範例程式碼"
BLOCK = re.compile(
    r"(<!-- example-source: ([a-z0-9_]+) -->).*?(<!-- /example-source -->)", re.S
)
REPOSITORY = "https://github.com/JasonChiu1984/python-note"


def source_block(match: re.Match) -> str:
    start, project, end = match.groups()
    folder = PROJECTS / project
    # Only source locations used by the teaching projects; skip build outputs
    # and virtual environments that students may have created locally.
    files = list(folder.glob("*.py"))
    for source_dir in ("src", "scripts", "tests", "hvac_monitor"):
        files.extend(p for p in (folder / source_dir).rglob("*") if p.suffix in {".py", ".pyx"})
    if not files:
        raise ValueError(f"No example source in {folder}")
    encoded_project = quote(folder.relative_to(ROOT).as_posix())
    rows = [start, f'<p class="example-repo"><a href="{REPOSITORY}/tree/main/{encoded_project}">在 GitHub 開啟專案資料夾</a></p>']
    def reading_order(path: Path) -> tuple:
        relative = path.relative_to(folder)
        return (relative.parts[0] == "tests" or path.name.startswith("test_"),
                path.name == "__init__.py", relative.as_posix())
    for path in sorted(files, key=reading_order):
        name = path.relative_to(folder).as_posix()
        url = f"{REPOSITORY}/blob/main/{encoded_project}/{quote(name)}"
        code = escape(path.read_text(encoding="utf-8"), quote=False)
        rows.extend([
            f'<details class="example-file"><summary><code>{escape(name)}</code></summary>',
            f'<p><a href="{url}">在 GitHub 查看此檔案</a></p>',
            f'<pre tabindex="0"><code>{code}</code></pre></details>',
        ])
    return "\n".join([*rows, end])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    stale = []
    for page in sorted(ROOT.glob("*.html")):
        previous = page.read_text(encoding="utf-8")
        updated = BLOCK.sub(source_block, previous)
        if updated != previous:
            if options.check:
                stale.append(page.name)
            else:
                page.write_text(updated, encoding="utf-8")
    if stale:
        print("Refresh the example listings in", ", ".join(stale))
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
