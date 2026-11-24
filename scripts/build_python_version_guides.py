"""Build both standalone language editions of the Python 3.13 and 3.14 guides."""

import base64
import json
import re
from html import escape, unescape
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from build_python315_bilingual import Fragment


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "python-315-learning-kit/python-315-complete-guide.html"
CJK = re.compile(r"[\u3400-\u9fff]")
ENGLISH_DIAGRAMS = {
    "production-notes-cli-fixed.svg": "Production notes-cli workflow",
    "python-project-delivery-blueprint.svg": "Python project delivery blueprint",
}
EXTRA_CSS = """
a:focus-visible, pre:focus-visible, .table-scroll:focus-visible {
    outline: 2px solid #147c7b; outline-offset: 3px;
}
.hero .links { display: flex; flex-wrap: wrap; gap: 7px 22px; margin-top: 18px; }
.hero a, .hero a:visited { color: #b1ece7; }
.diagram img { min-width: 0; }
h2, h3 { overflow-wrap: anywhere; }
html { scroll-padding-top: 84px; }
.language-bar {
    position: sticky;
    top: 0;
    z-index: 3;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 8px max(16px, calc((100vw - 1450px) / 2));
    background: #fff;
    border-bottom: 1px solid var(--line);
}
.language-bar .brand { color: var(--ink); font-weight: 750; text-decoration: none; }
.language-buttons { display: flex; gap: 4px; padding: 4px; background: #edf3f6; border-radius: 9px; }
.language-buttons a, .language-buttons span {
    display: inline-flex;
    align-items: center;
    min-height: 40px;
    padding: 5px 12px;
    border-radius: 6px;
    color: #344b61;
    font-size: 14px;
    font-weight: 700;
    white-space: nowrap;
    text-decoration: none;
}
.language-buttons a:hover { background: #dbece9; }
.language-buttons [aria-current] { background: #126f6d; color: #fff; }
aside { top: 84px; max-height: calc(100vh - 104px); }
@media (max-width: 920px) { aside { max-height: 300px; } }
@media print {
    .language-bar, .hero .links { display: none; }
    .table-scroll { overflow: visible; }
    table { min-width: 0; }
}
"""


def localize_inline(
    tokens: list[Token], kit: Path, engine: MarkdownIt, messages: dict[str, str] | None
) -> None:
    used = set()
    for token in tokens:
        if token.type != "inline":
            continue
        for child in token.children or []:
            if child.type != "image":
                continue
            src = child.attrGet("src")
            diagram = kit / src
            if diagram.parent != kit or diagram.suffix != ".svg":
                raise ValueError(f"Expected a local SVG in {kit}: {src}")
            if messages is not None:
                diagram = diagram.with_suffix(".en.svg")
                child.content = ENGLISH_DIAGRAMS[src]
                child.children = [Token("text", "", 0, content=child.content)]
            encoded = base64.b64encode(diagram.read_bytes()).decode("ascii")
            child.attrSet("src", f"data:image/svg+xml;base64,{encoded}")
            child.attrSet("class", "diagram-image")
            child.attrSet("style", "max-width:100%;height:auto;border-radius:8px")
        if messages is None:
            continue
        source = engine.renderer.renderInline(token.children or [], engine.options, {})
        if not CJK.search("".join(Fragment(source).prose)):
            continue
        if source not in messages:
            raise ValueError(f"Missing translation in {kit.name}: {source}")
        translation = messages[source]
        original = Fragment(source)
        translated = Fragment(translation)
        if CJK.search("".join(translated.prose)) or original.protected != translated.protected:
            raise ValueError(f"Check translation prose and inline code in {kit.name}: {source}")
        if re.findall(r'<a href="([^"]+)"', source) != re.findall(r'<a href="([^"]+)"', translation):
            raise ValueError(f"Translation changed link destinations in {kit.name}: {source}")
        token.children = [Token("html_inline", "", 0, content=translation)]
        used.add(source)
    if messages is not None and used != messages.keys():
        raise ValueError(f"Remove stale translations in {kit.name}")


def build(version: int, css: str, english: bool) -> None:
    name = f"python-{version}-complete-guide"
    kit = ROOT / f"python-{version}-learning-kit"
    source = (kit / f"{name}.md").read_text(encoding="utf-8")
    engine = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = engine.parse(source)
    messages = json.loads((kit / "translations/en.json").read_text(encoding="utf-8")) if english else None
    localize_inline(tokens, kit, engine, messages)

    def text(token):
        rendered = engine.renderer.renderInline(token.children or [], engine.options, {})
        return escape(unescape(re.sub(r"<[^>]*>", "", rendered)))

    title = text(tokens[1])
    tokens = tokens[3:]
    toc = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag in {"h2", "h3"}:
            ident = f"section-{len(toc) + 1:02}"
            token.attrSet("id", ident)
            toc.append(f'<a class="toc-{token.tag}" href="#{ident}">{text(tokens[index + 1])}</a>')
    article = engine.renderer.render(tokens, engine.options, {})
    table_label = "Data table" if english else "表格"
    article = article.replace(
        "<table>", f'<div class="table-scroll" role="region" aria-label="{table_label}" tabindex="0"><table>'
    ).replace("</table>", "</table></div>")
    article = re.sub(r"<pre>", '<pre tabindex="0">', article)

    if english:
        subtitle = "Core syntax, release changes, concurrency, and an HVAC simulation"
        skip, contents = "Skip to the guide", "Chapter contents"
        markdown, examples, verification = "Chinese Markdown source", "Example instructions (Chinese)", "Verification record"
        footer, language, lang_label = "Python Learning Notes", "en", "Reading language"
        language_links = f'<a href="{name}.html" lang="zh-Hant" hreflang="zh-Hant" data-switch>中文</a><span lang="en" aria-current="page">English</span>'
    else:
        subtitle = "核心語法、版本變更、並行應用與 HVAC 模擬實作"
        skip, contents = "跳至教材正文", "章節目錄"
        markdown, examples, verification = "Markdown 原稿", "範例執行方式", "驗證紀錄"
        footer, language, lang_label = "Python 學習筆記", "zh-Hant", "閱讀語言"
        language_links = f'<span lang="zh-Hant" aria-current="page">中文</span><a href="{name}.en.html" lang="en" hreflang="en" data-switch>English</a>'
    page = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}{EXTRA_CSS}</style>
</head>
<body id="top">
<div class="language-bar">
  <a class="brand" href="#top">Python {version // 100}.{version % 100}</a>
  <nav class="language-buttons" aria-label="{lang_label}">{language_links}</nav>
</div>
<header class="hero">
  <a href="#content">{skip}</a>
  <h1>{title}</h1>
  <p>{subtitle}</p>
  <div class="links">
    <a href="{name}.md">{markdown}</a>
    <a href="README.md">{examples}</a>
    <a href="verification.json">{verification}</a>
  </div>
</header>
<div class="layout">
  <aside><h2>{contents}</h2><nav aria-label="{contents}">{''.join(toc)}</nav></aside>
  <main id="content" tabindex="-1">{article}</main>
</div>
<footer>{footer} · 2026-11-24</footer>
<script>
  const otherLanguage = document.querySelector("[data-switch]");
  const edition = new URL(otherLanguage.href);
  function syncChapterLink() {{
    edition.hash = window.location.hash;
    otherLanguage.href = edition.href;
  }}
  window.addEventListener("hashchange", syncChapterLink);
  syncChapterLink();
</script>
</body>
</html>
"""
    suffix = ".en.html" if english else ".html"
    (kit / f"{name}{suffix}").write_text(page, encoding="utf-8")
    print(f"{name}{suffix}: {len(toc)} headings")


if __name__ == "__main__":
    base_style = REFERENCE.read_text(encoding="utf-8").split("<style>", 1)[1].split("</style>", 1)[0]
    base_style = base_style.split("td.linenos .normal", 1)[0]
    for version in (313, 314):
        for english in (False, True):
            build(version, base_style, english)
