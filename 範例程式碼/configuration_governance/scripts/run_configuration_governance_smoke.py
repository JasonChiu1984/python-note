from __future__ import annotations

import tempfile
from pathlib import Path

from configuration_governance.report import write_config_report
from configuration_governance.testing import make_loader, make_secret_file


def main() -> None:
    loader = make_loader()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        secret_path = make_secret_file(tmpdir_path / "secrets.json", token="prod-secret-token", port=9500)
        loaded = loader.load(
            env={
                "APP_API_TOKEN": "env-token",
                "APP_HOST": "192.168.10.50",
                "APP_WRITE_ENABLED": "false",
            },
            secret_file=secret_path,
            cli_overrides={"request_timeout_seconds": 7.5},
        )
        report_path = tmpdir_path / "config_report.json"
        write_config_report(report_path, loaded)
        payload = report_path.read_text(encoding="utf-8")
        if "***REDACTED***" not in payload:
            raise RuntimeError("config report must redact api_token")
        print("configuration governance smoke passed: precedence + validation + redaction")
        print(report_path)


if __name__ == "__main__":
    main()
