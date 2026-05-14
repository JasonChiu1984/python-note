from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class FeatureFlagMetadata:
    enabled: bool
    owner: str
    expires_on: str


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    request_timeout_seconds: float
    poll_interval_seconds: float
    device_timeout_seconds: float
    write_enabled: bool
    api_token: str
    schema_version: int = 1
    feature_flags: dict[str, FeatureFlagMetadata] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfigSource:
    host: str = "0.0.0.0"
    port: int = 8080
    request_timeout_seconds: float = 5.0
    poll_interval_seconds: float = 10.0
    device_timeout_seconds: float = 2.0
    write_enabled: bool = False
    api_token: str = ""
    feature_flags: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass(frozen=True)
class LoadedConfig:
    config: AppConfig
    effective_values: dict[str, object]
    source_map: dict[str, str]
    precedence: list[str]
    redacted_fields: set[str]


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"invalid bool: {value}")


class ConfigurationLoader:
    precedence = ["defaults", "env", "secret_file", "cli"]

    def __init__(self, defaults: ConfigSource, *, redacted_fields: set[str] | None = None) -> None:
        self.defaults = defaults
        self.redacted_fields = redacted_fields or {"api_token"}

    def load(
        self,
        *,
        env: dict[str, str] | None = None,
        secret_file: Path | None = None,
        cli_overrides: dict[str, object] | None = None,
    ) -> LoadedConfig:
        merged: dict[str, object] = {
            "host": self.defaults.host,
            "port": self.defaults.port,
            "request_timeout_seconds": self.defaults.request_timeout_seconds,
            "poll_interval_seconds": self.defaults.poll_interval_seconds,
            "device_timeout_seconds": self.defaults.device_timeout_seconds,
            "write_enabled": self.defaults.write_enabled,
            "api_token": self.defaults.api_token,
            "feature_flags": dict(self.defaults.feature_flags),
        }
        source_map = {key: "defaults" for key in merged}
        if env:
            self._apply_env(merged, source_map, env)
        if secret_file:
            self._apply_secret_file(merged, source_map, secret_file)
        if cli_overrides:
            self._apply_mapping(merged, source_map, cli_overrides, source_name="cli")
        config = self._build_config(merged)
        effective = self._redacted_effective_values(config)
        return LoadedConfig(
            config=config,
            effective_values=effective,
            source_map=source_map,
            precedence=list(self.precedence),
            redacted_fields=set(self.redacted_fields),
        )

    def _apply_env(self, merged: dict[str, object], source_map: dict[str, str], env: dict[str, str]) -> None:
        mapping: dict[str, object] = {}
        aliases = {
            "APP_HOST": "host",
            "APP_PORT": "port",
            "APP_REQUEST_TIMEOUT_SECONDS": "request_timeout_seconds",
            "APP_POLL_INTERVAL_SECONDS": "poll_interval_seconds",
            "APP_DEVICE_TIMEOUT_SECONDS": "device_timeout_seconds",
            "APP_WRITE_ENABLED": "write_enabled",
            "APP_API_TOKEN": "api_token",
            "APP_FEATURE_FLAGS_JSON": "feature_flags",
        }
        for key, target in aliases.items():
            if key not in env:
                continue
            value: object = env[key]
            if target == "feature_flags":
                value = json.loads(value)
            mapping[target] = value
        self._apply_mapping(merged, source_map, mapping, source_name="env")

    def _apply_secret_file(self, merged: dict[str, object], source_map: dict[str, str], secret_file: Path) -> None:
        payload = json.loads(secret_file.read_text(encoding="utf-8"))
        self._apply_mapping(merged, source_map, payload, source_name="secret_file")

    def _apply_mapping(
        self,
        merged: dict[str, object],
        source_map: dict[str, str],
        values: dict[str, object],
        *,
        source_name: str,
    ) -> None:
        for key, value in values.items():
            if key not in merged:
                continue
            merged[key] = value
            source_map[key] = source_name

    def _build_config(self, merged: dict[str, object]) -> AppConfig:
        port = int(merged["port"])
        if not 1 <= port <= 65535:
            raise ConfigError("port out of range")
        request_timeout_seconds = float(merged["request_timeout_seconds"])
        poll_interval_seconds = float(merged["poll_interval_seconds"])
        device_timeout_seconds = float(merged["device_timeout_seconds"])
        if request_timeout_seconds <= 0 or poll_interval_seconds <= 0 or device_timeout_seconds <= 0:
            raise ConfigError("timeouts and intervals must be positive")
        write_enabled = _parse_bool(merged["write_enabled"])
        api_token = str(merged["api_token"]).strip()
        if not api_token:
            raise ConfigError("API token required")
        feature_flags = {
            name: FeatureFlagMetadata(
                enabled=_parse_bool(payload.get("enabled", False)),
                owner=str(payload.get("owner", "")).strip() or "unassigned",
                expires_on=str(payload.get("expires_on", "")).strip() or "unspecified",
            )
            for name, payload in dict(merged["feature_flags"]).items()
        }
        return AppConfig(
            host=str(merged["host"]),
            port=port,
            request_timeout_seconds=request_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            device_timeout_seconds=device_timeout_seconds,
            write_enabled=write_enabled,
            api_token=api_token,
            feature_flags=feature_flags,
        )

    def _redacted_effective_values(self, config: AppConfig) -> dict[str, object]:
        return {
            "schema_version": config.schema_version,
            "host": config.host,
            "port": config.port,
            "request_timeout_seconds": config.request_timeout_seconds,
            "poll_interval_seconds": config.poll_interval_seconds,
            "device_timeout_seconds": config.device_timeout_seconds,
            "write_enabled": config.write_enabled,
            "api_token": "***REDACTED***" if "api_token" in self.redacted_fields else config.api_token,
            "feature_flags": {
                name: {
                    "enabled": metadata.enabled,
                    "owner": metadata.owner,
                    "expires_on": metadata.expires_on,
                }
                for name, metadata in config.feature_flags.items()
            },
        }
