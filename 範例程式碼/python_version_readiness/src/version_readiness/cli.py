from __future__ import annotations

import json

from .compat import build_readiness_report


def main() -> None:
    print(json.dumps(build_readiness_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

