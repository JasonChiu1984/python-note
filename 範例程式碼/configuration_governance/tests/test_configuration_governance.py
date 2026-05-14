from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from configuration_governance.loader import ConfigError
from configuration_governance.report import write_config_report
from configuration_governance.testing import make_loader, make_secret_file


class ConfigurationGovernanceTests(unittest.TestCase):
    def test_env_overrides_defaults(self) -> None:
        loaded = make_loader().load(env={"APP_API_TOKEN": "env-token", "APP_PORT": "9100"})
        self.assertEqual(loaded.config.port, 9100)
        self.assertEqual(loaded.source_map["port"], "env")

    def test_secret_file_overrides_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_path = make_secret_file(Path(tmpdir) / "secrets.json", token="secret-token", port=9300)
            loaded = make_loader().load(
                env={"APP_API_TOKEN": "env-token", "APP_PORT": "9100"},
                secret_file=secret_path,
            )
        self.assertEqual(loaded.config.api_token, "secret-token")
        self.assertEqual(loaded.config.port, 9300)
        self.assertEqual(loaded.source_map["api_token"], "secret_file")

    def test_cli_overrides_secret_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_path = make_secret_file(Path(tmpdir) / "secrets.json", token="secret-token", port=9300)
            loaded = make_loader().load(
                secret_file=secret_path,
                cli_overrides={"port": 9400, "write_enabled": True},
            )
        self.assertEqual(loaded.config.port, 9400)
        self.assertTrue(loaded.config.write_enabled)
        self.assertEqual(loaded.source_map["port"], "cli")

    def test_missing_token_fails_fast(self) -> None:
        with self.assertRaises(ConfigError):
            make_loader().load()

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            make_loader().load(env={"APP_API_TOKEN": "env-token", "APP_PORT": "70000"})

    def test_report_redacts_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_path = make_secret_file(Path(tmpdir) / "secrets.json", token="secret-token")
            loaded = make_loader().load(secret_file=secret_path)
            target = Path(tmpdir) / "config_report.json"
            write_config_report(target, loaded)
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["effective_values"]["api_token"], "***REDACTED***")
        self.assertEqual(payload["source_map"]["api_token"], "secret_file")


if __name__ == "__main__":
    unittest.main()
