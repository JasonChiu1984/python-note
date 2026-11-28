"""Extension build contract: stale and unavailable inputs must fail without writes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(root, *args, env=None):
    return subprocess.run([sys.executable, str(root / "scripts" / "build_extensions.py"), *args],
                          capture_output=True, text=True, cwd=root, timeout=900, env=env)


def test_extension_sections_are_current():
    proc = run(ROOT, "--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "checked 93 examples; 186 runs" in proc.stdout


def fixture(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts" / "build_extensions.py", tmp_path / "scripts" / "build_extensions.py")
    kit = tmp_path / "python-313-learning-kit"
    kit.mkdir()
    page = kit / "p.html"
    page.write_text("<html><body><main></main></body></html>")
    folder = tmp_path / "extensions" / "python-313-learning-kit__p"
    folder.mkdir(parents=True)
    meta = folder / "meta.json"
    meta.write_text(json.dumps({"example_title": "Synthetic"}))
    (folder / "example.py").write_text("print('test output')\n")
    return page, kit / "extension-example.py", meta


def test_check_does_not_write_stale_kit(tmp_path):
    page, local, _ = fixture(tmp_path)
    built = run(tmp_path)
    assert built.returncode == 0, built.stderr
    local.write_text("stale copy")
    before = page.read_bytes(), local.read_bytes()
    out = run(tmp_path, "--check")
    assert out.returncode != 0 and "extension-example.py" in out.stdout
    assert before == (page.read_bytes(), local.read_bytes())


def test_required_interpreter_and_package_cannot_be_skipped(tmp_path):
    page, local, meta = fixture(tmp_path)
    before = page.read_bytes()
    meta.write_text(json.dumps({"example_title": "Synthetic", "min_python": [3, 99]}))
    env = dict(os.environ)
    env.pop("EXT_PYTHON_399", None)
    out = run(tmp_path, "--check", env=env)
    assert out.returncode != 0 and "EXT_PYTHON_399" in out.stderr
    meta.write_text(json.dumps({"example_title": "Synthetic", "requires": ["_nonexistent_extension_fixture_"]}))
    out = run(tmp_path, "--check")
    assert out.returncode != 0 and "_nonexistent_extension_fixture_" in out.stderr
    assert page.read_bytes() == before and not local.exists()


GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40" role="img" '
    'aria-labelledby="dg-t-title dg-t-desc"><title id="dg-t-title">T</title><desc id="dg-t-desc">D</desc>'
    '<rect x="1" y="1" width="98" height="38" fill="none" stroke="currentColor"/></svg>'
)


def with_diagram(tmp_path, svg):
    page, _, meta = fixture(tmp_path)
    (meta.parent / "diagram-a.svg").write_text(svg, encoding="utf-8")
    meta.write_text(json.dumps({"example_title": "Synthetic", "diagrams": [
        {"kind": "flow", "title": "Flow", "file": "diagram-a.svg", "caption": "cap"}]}))
    return page


def test_diagram_is_inlined_between_markers(tmp_path):
    page = with_diagram(tmp_path, GOOD_SVG)
    built = run(tmp_path)
    assert built.returncode == 0, built.stderr
    assert "1 diagram(s)" in built.stdout
    html = page.read_text(encoding="utf-8")
    start, end = html.index("<!-- diagram:start -->"), html.index("<!-- diagram:end -->")
    assert start < html.index('<svg xmlns="http://www.w3.org/2000/svg"') < end
    assert 'data-kind="flow"' in html and "<figcaption>" in html
    assert run(tmp_path, "--check").returncode == 0


def test_unsafe_or_inaccessible_svg_fails_without_writes(tmp_path):
    bad_variants = [
        GOOD_SVG.replace('<desc id="dg-t-desc">D</desc>', "").replace(" dg-t-desc", ""),
        GOOD_SVG.replace("<rect", '<script>alert(1)</script><rect'),
        GOOD_SVG.replace('viewBox="0 0 100 40"', 'viewBox="0 0 100 40" width="100"'),
        GOOD_SVG.replace("<rect", '<image href="https://example.com/x.png"/><rect'),
        GOOD_SVG.replace('id="dg-t-title"', 'id="title"').replace("dg-t-title ", "title "),
    ]
    for n, svg in enumerate(bad_variants):
        root = tmp_path / str(n)
        root.mkdir()
        page = with_diagram(root, svg)
        before = page.read_bytes()
        out = run(root)
        assert out.returncode != 0, (n, out.stdout)
        assert page.read_bytes() == before
