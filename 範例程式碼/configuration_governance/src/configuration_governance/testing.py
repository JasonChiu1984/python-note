from __future__ import annotations

from pathlib import Path

from .loader import ConfigSource, ConfigurationLoader


def make_loader() -> ConfigurationLoader:
    defaults = ConfigSource(
        host="127.0.0.1",
        port=8080,
        request_timeout_seconds=5.0,
        poll_interval_seconds=10.0,
        device_timeout_seconds=2.0,
        write_enabled=False,
        api_token="",
        feature_flags={
            "new_parser": {
                "enabled": False,
                "owner": "platform-team",
                "expires_on": "2026-06-30",
            }
        },
    )
    return ConfigurationLoader(defaults)


def make_secret_file(path: Path, *, token: str, port: int = 9200) -> Path:
    path.write_text(
        (
            "{\n"
            f'  "api_token": "{token}",\n'
            f'  "port": {port},\n'
            '  "feature_flags": {"new_parser": {"enabled": true, "owner": "platform-team", "expires_on": "2026-06-30"}}\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    return path
