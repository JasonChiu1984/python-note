from scripts.validate_tutorial_catalog import validate


def site(root, **files):
    for path, html in files.items():
        dst = root / path.replace("__", "/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(html, encoding="utf-8")
    return root


def test_indirect_topic_does_not_require_progress(tmp_path):
    root = site(tmp_path, **{
        "index.html": '<a href="guide/">Guide</a><output id="intro"></output><script>showProgress("intro","lab",1);</script>',
        "guide__index.html": '<a href="../python_topic_tutorial.html?lang=zh#chapter">Topic</a>',
        "python_topic_tutorial.html": '<a id="chapter" href="index.html">Home</a>',
    })
    assert validate(root) == []


def test_true_orphan_while_legacy_alias_is_exempt(tmp_path):
    root = site(tmp_path, **{"index.html": "<title>Home</title>",
                           "python_orphan_tutorial.html": "<p>Unlinked</p>",
                           "python_interactive_tutorial.html": "<p>Legacy</p>"})
    assert validate(root) == ["tutorial pages unreachable from index: python_orphan_tutorial.html"]


def test_missing_progress_target_and_duplicate_storage_key(tmp_path):
    root = site(tmp_path, **{"index.html": '''<output id="visible"></output><script>
        showProgress("gone", "same", 2); showProgress('visible', 'same', 0);</script>'''})
    findings = validate(root)
    assert len(findings) == 3
    assert any("'gone'" in item and "ID" in item for item in findings)
    assert any("positive total" in item for item in findings)
    assert "duplicate progress storage key: same" in findings


def test_broken_nested_link(tmp_path):
    root = site(tmp_path, **{"index.html": '<a href="guide/reading.html">Guide</a>',
                           "guide__reading.html": '<a href="../missing.html#id">Missing</a>'})
    assert validate(root) == ["guide/reading.html: missing local HTML target missing.html"]


def test_comments_and_external_links_do_not_create_reachability(tmp_path):
    root = site(tmp_path, **{
        "index.html": '<!-- <a href="python_hidden_tutorial.html">Hidden</a> -->'
                      '<a href="https://example.invalid/python_hidden_tutorial.html">External</a>',
        "python_hidden_tutorial.html": "<p>Hidden</p>",
    })
    assert validate(root) == ["tutorial pages unreachable from index: python_hidden_tutorial.html"]
