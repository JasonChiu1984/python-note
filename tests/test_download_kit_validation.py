from zipfile import ZipFile

from scripts.validate_download_kits import validate_archive


def fixture_kit(tmp_path, pages, *, archive_overrides=None):
    archive = tmp_path / "sample-learning-kit.zip"
    for name, body in pages.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    with ZipFile(archive, "w") as zf:
        for name, body in (pages | (archive_overrides or {})).items():
            zf.writestr(name, body)
    return archive


def test_accepts_local_targets_and_explicit_online_navigation(tmp_path):
    files = {
        "kit/index.html": '<a href="./guide%20one.html#reading">Read</a><a href="https://example.org/">Online</a>',
        "kit/guide one.html": '<h1 id="reading">Reading</h1>',
    }
    assert validate_archive(fixture_kit(tmp_path, files), tmp_path) == []


def test_reports_missing_relative_and_root_relative_targets(tmp_path):
    files = {"kit/index.html": '<a href="../index.html">Home</a><img src="/diagram.svg">'}
    errors = validate_archive(fixture_kit(tmp_path, files), tmp_path)
    assert len(errors) == 2
    assert any("missing offline target ../index.html" in error for error in errors)
    assert any("root-relative offline link /diagram.svg" in error for error in errors)


def test_detects_stale_packaged_bytes_and_broken_fragment(tmp_path):
    files = {"kit/index.html": '<h1 id="new">New</h1>'}
    archive = fixture_kit(tmp_path, files, archive_overrides={"kit/index.html": '<a href="#old">Old</a>'})
    errors = validate_archive(archive, tmp_path)
    assert len(errors) == 2
    assert any("source mismatch" in error for error in errors)
    assert any("missing offline fragment #old" in error for error in errors)
