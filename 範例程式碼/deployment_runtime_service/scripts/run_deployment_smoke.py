#!/usr/bin/env python3
"""Run a local deployment-runtime smoke check without requiring Docker."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

from deployment_runtime_service.config import load_config
from deployment_runtime_service.deployment_contract import validate_deployment_files
from deployment_runtime_service.health import RuntimeState, health_report, readiness_report
from deployment_runtime_service.logging_utils import log_json


def main() -> int:
    config = load_config({
        "APP_NAME": "deployment-runtime-service",
        "APP_HOST": "127.0.0.1",
        "APP_PORT": "8080",
        "APP_ENV": "smoke",
        "DEPENDENCY_STATUS": "healthy",
        "SHUTDOWN_TIMEOUT_SECONDS": "10",
    })
    state = RuntimeState.started_now()
    health_code, health_payload = health_report(config, state)
    ready_code, ready_payload = readiness_report(config, state)
    missing = validate_deployment_files(PROJECT_ROOT)

    if health_code != 200 or ready_code != 200:
        print(json.dumps({"health": health_payload, "ready": ready_payload}, ensure_ascii=False))
        return 1
    if any(missing.values()):
        print(json.dumps(missing, ensure_ascii=False, indent=2))
        return 1

    log_json("deployment_smoke", service=config.app_name, environment=config.environment, token="redacted-by-helper")
    print("deployment runtime smoke passed: config + health + readiness + deployment files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
