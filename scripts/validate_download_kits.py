"""Check shipped ZIP integrity, parity with the repo, and offline HTML references."""
import posixpath
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile


class OfflineReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.targets = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.targets.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.targets.add(attrs["name"])
        key = {
            "a": "href", "img": "src", "script": "src",
            "iframe": "src", "source": "src", "link": "href",
        }.get(tag)
        if key and attrs.get(key):
            self.refs.append(attrs[key])


def validate_archive(archive, root):
    issues = []
    with ZipFile(archive) as kit:
        if bad := kit.testzip():
            return [f"{archive.name}: invalid CRC for {bad}"]
        members = [item.filename for item in kit.infolist() if not item.is_dir()]
        paths = set(members)
        docs = {}
        if len(paths) != len(members):
            issues.append(f"{archive.name}: duplicate member names")
        for path in sorted(paths):
            if path.startswith("/") or "\\" in path or ".." in path.split("/"):
                issues.append(f"{archive.name}: invalid member path {path}")
                continue
            data = kit.read(path)
            source = root / path
            if not source.is_file() or source.read_bytes() != data:
                issues.append(f"{archive.name}: source mismatch for {path}")
            if path.endswith(".html"):
                docs[path] = doc = OfflineReferences()
                doc.feed(data.decode("utf-8"))
        for path, doc in docs.items():
            for ref in doc.refs:
                url = urlsplit(ref)
                if url.netloc or url.scheme:
                    continue
                target = unquote(url.path)
                if target.startswith("/"):
                    issues.append(f"{archive.name}: {path}: root-relative offline link {ref}")
                    continue
                if target.endswith("/"):
                    target += "index.html"
                target = posixpath.normpath(posixpath.join(posixpath.dirname(path), target)) if target else path
                if target not in paths:
                    issues.append(f"{archive.name}: {path}: missing offline target {ref}")
                elif url.fragment and target in docs and unquote(url.fragment) not in docs[target].targets:
                    issues.append(f"{archive.name}: {path}: missing offline fragment {ref}")
    return issues


def main():
    root = Path(__file__).resolve().parents[1]
    kits = sorted(root.glob("*-learning-kit.zip"))
    if not kits:
        raise SystemExit("No learning-kit ZIP files found")
    issues = [issue for kit in kits for issue in validate_archive(kit, root)]
    if issues:
        raise SystemExit("\n".join(issues))
    print(f"Download validation passed: {len(kits)} ZIPs, source parity and offline links")


if __name__ == "__main__":
    main()
