"""Check tutorial reachability and declared homepage progress independently."""
from __future__ import annotations

from collections import Counter, deque
from html.parser import HTMLParser
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ORPHAN_PAGES = {"python_interactive_tutorial.html"}
PROGRESS_CALL = re.compile(
    r"""\bshowProgress\(\s*(["'])(.*?)\1\s*,\s*(["'])(.*?)\3\s*,\s*(-?\d+)\s*\)"""
)


class Page(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.ids: Counter[str] = Counter()
        self.scripts: list[str] = []
        self._script = False
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids[attributes["id"]] += 1
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag == "script":
            self._script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._script = False

    def handle_data(self, data):
        if self._script:
            self.scripts.append(data)


def html_target(root: Path, source: Path, href: str) -> Path | None:
    """Resolve a local HTML navigation target, ignoring fragments and queries."""
    try:
        url = urlsplit(href)
    except ValueError:
        return None
    if url.scheme or url.netloc or not url.path:
        return None
    value = unquote(url.path)
    target = (root / value.lstrip("/") if value.startswith("/") else root / source.parent / value).resolve()
    if target.is_dir() or value.endswith("/"):
        target = target / "index.html"
    if target.suffix.lower() not in {".html", ".htm"}:
        return None
    try:
        return target.relative_to(root)
    except ValueError:
        return None


def defects_for_progress(page: Page) -> list[str]:
    entries = [(target, key, int(total))
               for _, target, _, key, total in PROGRESS_CALL.findall("\n".join(page.scripts))]
    errors = []
    for target, key, total in entries:
        if page.ids[target] != 1:
            errors.append(f"progress target {target!r} must match exactly one homepage ID")
        if not key.strip() or total < 1:
            errors.append(f"progress target {target!r} must have a key and a positive total")
    for i, label in ((0, "target"), (1, "storage key")):
        for name, count in Counter(entry[i] for entry in entries).items():
            if count > 1:
                errors.append(f"duplicate progress {label}: {name}")
    return errors


def validate(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    home = Path("index.html")
    if not (root / home).is_file():
        return ["missing homepage: index.html"]
    queue = deque([home])
    reachable = {home}
    missing: set[tuple[str, str]] = set()
    errors = []
    while queue:
        source = queue.popleft()
        page = Page((root / source).read_text(encoding="utf-8"))
        if source == home:
            errors.extend(defects_for_progress(page))
        for href in page.links:
            target = html_target(root, source, href)
            if target is None:
                continue
            if not (root / target).is_file():
                missing.add((str(source), str(target)))
            elif target not in reachable:
                reachable.add(target)
                queue.append(target)

    for source, target in sorted(missing):
        errors.append(f"{source}: missing local HTML target {target}")
    catalog = {p.relative_to(root) for glob in ("python_*tutorial.html", "python_*cases.html")
               for p in root.glob(glob) if p.is_file()}
    missing_from_catalog = sorted(map(str, catalog - reachable - set(map(Path, LEGACY_ORPHAN_PAGES))))
    if missing_from_catalog:
        errors.append(f"tutorial pages unreachable from index: {', '.join(missing_from_catalog)}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"catalog_validation_error: {error}")
        return 1
    print("tutorial catalog validation passed: reachability, local HTML links, and declared progress bindings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
