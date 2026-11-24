"""Validate and embed the guide's English messages, diagrams, CSS, and JavaScript.

The published HTML remains self-contained. This maintainer utility uses only the
standard library and can be rerun after editing translations or switch assets.
"""

from __future__ import annotations

import base64
import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "python-315-learning-kit"
PAGE = KIT / "python-315-complete-guide.html"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class TranslationNodes(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_offsets = [0]
        for match in re.finditer("\n", source):
            self.line_offsets.append(match.end())
        self.stack: list[tuple[str, str | None, int]] = []
        self.nodes: dict[str, str] = {}

    def absolute_position(self) -> int:
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        key = dict(attrs).get("data-i18n")
        self.stack.append((tag, key, self.absolute_position() + len(self.get_starttag_text())))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError(f"Unbalanced HTML near </{tag}>")
        _, key, start = self.stack.pop()
        if key:
            if key in self.nodes:
                raise ValueError(f"Duplicate translation key: {key}")
            self.nodes[key] = self.source[start:self.absolute_position()]


class Fragment(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.signature = []
        self.protected = []
        self.prose = []
        self.protected_depth = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.signature.append(("start", tag, sorted(attrs)))
        if tag in {"code", "pre"}:
            self.protected_depth += 1

    def handle_startendtag(self, tag, attrs):
        self.signature.append(("empty", tag, sorted(attrs)))

    def handle_endtag(self, tag):
        self.signature.append(("end", tag))
        if tag in {"code", "pre"}:
            self.protected_depth -= 1

    def handle_data(self, data):
        (self.protected if self.protected_depth else self.prose).append(data)


def replace_block(source: str, tag: str, identifier: str, body: str) -> str:
    pattern = rf'(<{tag}\b[^>]*\bid="{re.escape(identifier)}"[^>]*>).*?(</{tag}>)'
    updated, count = re.subn(pattern, lambda m: m[1] + body + m[2], source, flags=re.S)
    if count != 1:
        raise ValueError(f"Expected one {identifier} block; found {count}")
    return updated


def main() -> None:
    source = PAGE.read_text(encoding="utf-8")
    catalog = json.loads((KIT / "translations/en.json").read_text(encoding="utf-8"))
    parser = TranslationNodes(source)
    parser.feed(source)
    entries = catalog["messages"]
    if set(parser.nodes) != set(entries):
        raise ValueError("Page and translation keys differ; update the English catalog.")

    for key, entry in entries.items():
        if parser.nodes[key] != entry["source"]:
            raise ValueError(f"Chinese source changed without a translation review: {key}")
        original = Fragment(entry["source"])
        translated = Fragment(entry["translation"])
        if original.signature != translated.signature or original.protected != translated.protected:
            raise ValueError(f"Translation changed markup, a link, or code: {key}")
        if re.search(r"[\u3400-\u9fff]", "".join(translated.prose)):
            raise ValueError(f"Untranslated English prose: {key}")

    diagrams = {}
    for key, item in catalog["diagrams"].items():
        data = base64.b64encode((KIT / item["file"]).read_bytes()).decode("ascii")
        diagrams[key] = {"src": "data:image/svg+xml;base64," + data, "alt": item["alt"]}

    payload = {
        "title": catalog["title"],
        "messages": {key: entry["translation"] for key, entry in entries.items()},
        "diagrams": diagrams,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    source = replace_block(source, "script", "guide-translations", encoded)
    source = replace_block(source, "script", "guide-language-script", (KIT / "assets/language-switch.js").read_text(encoding="utf-8"))
    source = replace_block(source, "style", "guide-language-style", (KIT / "assets/language-switch.css").read_text(encoding="utf-8"))
    PAGE.write_text(source, encoding="utf-8")
    print(f"Embedded {len(entries)} translations and {len(diagrams)} English diagrams; source, markup, code, and links verified.")


if __name__ == "__main__":
    main()
