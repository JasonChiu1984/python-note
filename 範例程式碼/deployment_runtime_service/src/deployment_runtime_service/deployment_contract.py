"""Static checks for deployment files used by the tutorial."""

from __future__ import annotations

from pathlib import Path


REQUIRED_DOCKERFILE_TOKENS = [
    "FROM python:3.14-slim",
    "PYTHONUNBUFFERED=1",
    "useradd --create-home",
    "USER appuser",
    "HEALTHCHECK",
    "CMD [\"python\", \"-m\", \"deployment_runtime_service.server\"]",
]

REQUIRED_COMPOSE_TOKENS = [
    "services:",
    "deployment-runtime-service:",
    "APP_PORT:",
    "restart: unless-stopped",
    "healthcheck:",
    "resources:",
]

REQUIRED_DOCKERIGNORE_TOKENS = [
    ".venv",
    "__pycache__",
    ".env",
    "secrets",
]


def assert_contains(path: Path, tokens: list[str]) -> list[str]:
    content = path.read_text(encoding="utf-8")
    return [token for token in tokens if token not in content]


def validate_deployment_files(project_root: Path) -> dict[str, list[str]]:
    checks = {
        "Dockerfile": assert_contains(project_root / "Dockerfile", REQUIRED_DOCKERFILE_TOKENS),
        "compose.yaml": assert_contains(project_root / "compose.yaml", REQUIRED_COMPOSE_TOKENS),
        ".dockerignore": assert_contains(project_root / ".dockerignore", REQUIRED_DOCKERIGNORE_TOKENS),
    }
    return checks
