"""Sync each *-learning-kit.zip with its folder after extension sections are rebuilt.

Members that already exist are replaced with the current file bytes; files listed in ADD_PATTERNS that
exist in the kit folder but not in the ZIP are appended. Member order is preserved.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADD_PATTERNS = ("extension-example.py", "extension-example-en.py")


def refresh(zip_path: Path) -> int:
    kit_dir = ROOT / zip_path.stem
    with zipfile.ZipFile(zip_path) as z:
        infos = [(i, z.read(i.filename)) for i in z.infolist()]
    names = {i.filename for i, _ in infos}
    changed = 0
    tmp = zip_path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in infos:
            src = ROOT / info.filename
            if not info.is_dir() and src.is_file() and src.read_bytes() != data:
                data, changed = src.read_bytes(), changed + 1
            out.writestr(info, data)
        for name in ADD_PATTERNS:
            src = kit_dir / name
            member = f"{zip_path.stem}/{name}"
            if src.is_file() and member not in names:
                out.write(src, member)
                changed += 1
    tmp.replace(zip_path)
    return changed


if __name__ == "__main__":
    for z in sorted(ROOT.glob("*-learning-kit.zip")):
        print(z.name, refresh(z), "member(s) updated")
