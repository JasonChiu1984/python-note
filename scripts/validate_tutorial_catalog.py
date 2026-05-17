from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
LEGACY_ORPHAN_PAGES = {"python_interactive_tutorial.html"}


def collect_python_pages() -> set[str]:
    return {path.name for path in ROOT.glob("python_*tutorial.html")} | {
        path.name for path in ROOT.glob("python_*cases.html")
    }


def collect_index_links(index_text: str) -> list[str]:
    return re.findall(r'href="(python_[^"]+\.html)"', index_text)


def collect_progress_keys(index_text: str) -> list[tuple[str, str, int]]:
    return [
        (target, key, int(total))
        for target, key, total in re.findall(
            r'showProgress\("([^"]+)",\s*"([^"]+)",\s*(\d+)\);',
            index_text,
        )
    ]


def validate() -> list[str]:
    index_text = INDEX_PATH.read_text(encoding="utf-8")
    python_pages = collect_python_pages()
    linked_pages = collect_index_links(index_text)
    progress_entries = collect_progress_keys(index_text)
    errors: list[str] = []

    missing_targets = sorted(page for page in linked_pages if page not in python_pages)
    if missing_targets:
        errors.append(f"index links missing target pages: {', '.join(missing_targets)}")

    dom_ids = set(re.findall(r'id="([^"]+)"', index_text))
    missing_progress_ids = sorted(target for target, _, _ in progress_entries if target not in dom_ids)
    if missing_progress_ids:
        errors.append(f"showProgress targets missing DOM ids: {', '.join(missing_progress_ids)}")

    if len(progress_entries) != len(set(linked_pages)):
        errors.append(
            "showProgress entry count does not match linked tutorial count: "
            f"{len(progress_entries)} vs {len(set(linked_pages))}"
        )

    orphan_pages = sorted(python_pages - set(linked_pages) - LEGACY_ORPHAN_PAGES)
    if orphan_pages:
        errors.append(f"python tutorial pages not linked from index: {', '.join(orphan_pages)}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"catalog_validation_error: {error}")
        return 1

    print(
        "tutorial catalog validation passed: "
        "index links + tutorial files + progress entries are aligned"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
