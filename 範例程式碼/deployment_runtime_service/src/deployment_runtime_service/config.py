"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


@dataclass(frozen=True)
class RuntimeConfig:
    app_name: str
    host: str
    port: int
    environment: str
    dependency_status: str
    shutdown_timeout_seconds: float


def _read_int(env: dict[str, str], key: str, default: str) -> int:
    raw = env.get(key, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer") from exc


def _read_float(env: dict[str, str], key: str, default: str) -> float:
    raw = env.get(key, default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number") from exc


def load_config(env: dict[str, str] | None = None) -> RuntimeConfig:
    values = os.environ if env is None else env
    app_name = values.get("APP_NAME", "deployment-runtime-service").strip()
    host = values.get("APP_HOST", "0.0.0.0").strip()
    environment = values.get("APP_ENV", "local").strip()
    dependency_status = values.get("DEPENDENCY_STATUS", "healthy").strip().lower()
    port = _read_int(values, "APP_PORT", "8080")
    shutdown_timeout = _read_float(values, "SHUTDOWN_TIMEOUT_SECONDS", "10")

    if not app_name:
        raise ConfigError("APP_NAME is required")
    if not host:
        raise ConfigError("APP_HOST is required")
    if not (1 <= port <= 65535):
        raise ConfigError("APP_PORT must be between 1 and 65535")
    if dependency_status not in {"healthy", "degraded", "down"}:
        raise ConfigError("DEPENDENCY_STATUS must be healthy, degraded, or down")
    if shutdown_timeout <= 0:
        raise ConfigError("SHUTDOWN_TIMEOUT_SECONDS must be greater than zero")

    return RuntimeConfig(
        app_name=app_name,
        host=host,
        port=port,
        environment=environment,
        dependency_status=dependency_status,
        shutdown_timeout_seconds=shutdown_timeout,
    )
