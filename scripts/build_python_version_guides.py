"""Build the standalone 3.13 and 3.14 readers from their Markdown sources."""

import base64
import re
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "python-315-learning-kit/python-315-complete-guide.html"
EXTRA_CSS = """
a:focus-visible, pre:focus-visible, .table-scroll:focus-visible {
    outline: 2px solid #147c7b; outline-offset: 3px;
}
.hero .links { display: flex; flex-wrap: wrap; gap: 7px 22px; margin-top: 18px; }
.hero a, .hero a:visited { color: #b1ece7; }
.diagram img { min-width: 0; }
h2, h3 { overflow-wrap: anywhere; }
@media print { .hero .links { display: none; } .table-scroll { overflow: visible; } table { min-width: 0; } }
"""


def inline_images(tokens: list[Token], kit: Path) -> None:
    for token in tokens:
        if token.children:
            inline_images(token.children, kit)
        if token.type != "image":
            continue
        src = token.attrGet("src")
        diagram = kit / src
        if diagram.parent != kit or diagram.suffix != ".svg":
            raise ValueError(f"Expected a local SVG in {kit}: {src}")
        encoded = base64.b64encode(diagram.read_bytes()).decode("ascii")
        token.attrSet("src", f"data:image/svg+xml;base64,{encoded}")
        token.attrSet("class", "diagram-image")
        token.attrSet("alt", token.content)
        token.attrSet("style", "max-width:100%;height:auto;border-radius:8px")


def build(version: int, css: str) -> None:
    name = f"python-{version}-complete-guide"
    kit = ROOT / f"python-{version}-learning-kit"
    source = (kit / f"{name}.md").read_text(encoding="utf-8")
    engine = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = engine.parse(source)
    title = tokens[1].content
    tokens = tokens[3:]
    toc = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag in {"h2", "h3"}:
            ident = f"section-{len(toc) + 1:02}"
            token.attrSet("id", ident)
            heading = escape(tokens[index + 1].content)
            toc.append(f'<a class="toc-{token.tag}" href="#{ident}">{heading}</a>')
    inline_images(tokens, kit)
    article = engine.renderer.render(tokens, engine.options, {})
    article = article.replace(
        "<table>", '<div class="table-scroll" role="region" aria-label="表格" tabindex="0"><table>'
    ).replace("</table>", "</table></div>")
    article = re.sub(r"<pre>", '<pre tabindex="0">', article)
    title = escape(title)
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}{EXTRA_CSS}</style>
</head>
<body>
<header class="hero">
  <a href="#content">跳至教材正文</a>
  <h1>{title}</h1>
  <p>核心語法、版本變更、並行應用與 HVAC 模擬實作</p>
  <div class="links">
    <a href="{name}.md">Markdown 原稿</a>
    <a href="README.md">範例執行方式</a>
    <a href="verification.json">驗證紀錄</a>
  </div>
</header>
<div class="layout">
  <aside><h2>章節目錄</h2><nav aria-label="章節目錄">{''.join(toc)}</nav></aside>
  <main id="content" tabindex="-1">{article}</main>
</div>
<footer>Python 學習筆記 · 2026-11-24</footer>
</body>
</html>
"""
    (kit / f"{name}.html").write_text(page, encoding="utf-8")
    print(f"{name}.html: {len(toc)} headings")


if __name__ == "__main__":
    base_style = REFERENCE.read_text(encoding="utf-8").split("<style>", 1)[1].split("</style>", 1)[0]
    # Keep the reader layout and code-block styling, without the old syntax highlighter.
    base_style = base_style.split("td.linenos .normal", 1)[0]
    for version in (313, 314):
        build(version, base_style)
