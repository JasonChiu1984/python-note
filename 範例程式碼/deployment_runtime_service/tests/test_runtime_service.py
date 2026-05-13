from pathlib import Path
import json
import unittest

from deployment_runtime_service.config import ConfigError, load_config
from deployment_runtime_service.deployment_contract import validate_deployment_files
from deployment_runtime_service.health import RuntimeState, health_report, readiness_report
from deployment_runtime_service.logging_utils import log_json, redact


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeConfigTests(unittest.TestCase):
    def test_load_config_from_environment_mapping(self) -> None:
        config = load_config({
            "APP_NAME": "runtime-demo",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "8090",
            "APP_ENV": "test",
            "DEPENDENCY_STATUS": "healthy",
            "SHUTDOWN_TIMEOUT_SECONDS": "5",
        })

        self.assertEqual(config.app_name, "runtime-demo")
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8090)
        self.assertEqual(config.environment, "test")

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            load_config({"APP_PORT": "70000"})


class HealthContractTests(unittest.TestCase):
    def test_health_stays_ok_when_dependency_is_degraded(self) -> None:
        config = load_config({"DEPENDENCY_STATUS": "degraded"})
        status_code, payload = health_report(config, RuntimeState.started_now())

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")

    def test_readiness_fails_when_dependency_is_degraded(self) -> None:
        config = load_config({"DEPENDENCY_STATUS": "degraded"})
        status_code, payload = readiness_report(config, RuntimeState.started_now())

        self.assertEqual(status_code, 503)
        self.assertEqual(payload["status"], "not_ready")

    def test_readiness_fails_while_draining(self) -> None:
        config = load_config({"DEPENDENCY_STATUS": "healthy"})
        state = RuntimeState.started_now()
        state.mark_draining()

        status_code, payload = readiness_report(config, state)

        self.assertEqual(status_code, 503)
        self.assertEqual(payload["reason"], "service is draining")


class LoggingTests(unittest.TestCase):
    def test_redact_sensitive_values(self) -> None:
        payload = redact({"user": "operator", "token": "plain-secret"})

        self.assertEqual(payload["user"], "operator")
        self.assertEqual(payload["token"], "***")

    def test_log_json_returns_parseable_json(self) -> None:
        line = log_json("test_event", token="plain-secret", request_id="abc")
        payload = json.loads(line)

        self.assertEqual(payload["event"], "test_event")
        self.assertEqual(payload["token"], "***")


class DeploymentContractTests(unittest.TestCase):
    def test_deployment_files_contain_required_runtime_contracts(self) -> None:
        missing = validate_deployment_files(PROJECT_ROOT)

        self.assertEqual(missing, {"Dockerfile": [], "compose.yaml": [], ".dockerignore": []})


if __name__ == "__main__":
    unittest.main()
