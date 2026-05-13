"""Container healthcheck command."""

from __future__ import annotations

from .config import ConfigError, load_config
from .health import RuntimeState, health_report


def main() -> int:
    try:
        config = load_config()
    except ConfigError:
        return 2
    status_code, _payload = health_report(config, RuntimeState.started_now())
    return 0 if status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
