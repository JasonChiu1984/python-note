from __future__ import annotations

import unittest

from observability_operations.health import DependencyState, build_health_report
from observability_operations.service import ObservedService
from observability_operations.telemetry import TelemetryCollector


class ObservabilityOperationsTests(unittest.TestCase):
    def test_successful_request_records_log_metric_and_span(self) -> None:
        collector = TelemetryCollector()
        service = ObservedService(collector)

        response = service.handle_request("/orders", trace_id="trace-ok", dependency_latency_ms=40)

        self.assertTrue(response["ok"])
        self.assertEqual(collector.metrics_snapshot()["requests_total"], 1)
        self.assertEqual(collector.metrics_snapshot()["errors_total"], 0)
        self.assertEqual(collector.spans[0]["status"], "ok")
        self.assertEqual(collector.logs[0]["trace_id"], "trace-ok")

    def test_dependency_timeout_records_error_and_redacts_secret(self) -> None:
        collector = TelemetryCollector()
        service = ObservedService(collector)

        response = service.handle_request("/orders", trace_id="trace-timeout", dependency_latency_ms=150)

        self.assertFalse(response["ok"])
        metrics = collector.metrics_snapshot()
        self.assertEqual(metrics["errors_total"], 1)
        self.assertEqual(metrics["dependency_timeouts_total"], 1)
        error_logs = [item for item in collector.logs if item["event"] == "dependency.timeout"]
        self.assertEqual(error_logs[0]["token"], "***")

    def test_health_report_distinguishes_liveness_and_readiness(self) -> None:
        report = build_health_report([DependencyState(name="orders-db", ok=True, latency_ms=130)])

        self.assertEqual(report["live"], "ok")
        self.assertEqual(report["ready"], "fail")
        self.assertEqual(report["status"], "degraded")

    def test_slo_evaluation_fails_when_error_rate_is_too_high(self) -> None:
        collector = TelemetryCollector()
        service = ObservedService(collector)
        service.handle_request("/orders", trace_id="trace-ok", dependency_latency_ms=40)
        service.handle_request("/orders", trace_id="trace-timeout", dependency_latency_ms=180)

        slo = collector.evaluate_slo(max_error_rate=0.1, max_average_latency_ms=250)

        self.assertFalse(slo["passed"])
        self.assertGreater(slo["metrics"]["error_rate"], 0.1)


    def test_slo_with_no_samples_reports_no_data_not_pass(self) -> None:
        slo = TelemetryCollector().evaluate_slo()

        self.assertEqual(slo["status"], "no_data")
        self.assertFalse(slo["passed"])
        self.assertIsNone(slo["evaluated"]["error_rate"])
        self.assertIsNone(slo["evaluated"]["average_latency_ms"])

    def test_slo_uses_error_rate_before_display_rounding(self) -> None:
        collector = TelemetryCollector()
        for i in range(10010):
            collector.record_request(20.0, ok=i >= 501)

        slo = collector.evaluate_slo()
        self.assertEqual(slo["metrics"]["error_rate"], 0.05)
        self.assertGreater(slo["evaluated"]["error_rate"], 0.05)
        self.assertEqual(slo["status"], "fail")
        self.assertFalse(slo["passed"])

    def test_slo_uses_latency_before_display_rounding(self) -> None:
        collector = TelemetryCollector()
        collector.record_request(250.0004, ok=True)

        slo = collector.evaluate_slo()
        self.assertEqual(slo["metrics"]["average_latency_ms"], 250.0)
        self.assertGreater(slo["evaluated"]["average_latency_ms"], 250.0)
        self.assertEqual(slo["status"], "fail")
        self.assertFalse(slo["passed"])

    def test_slo_exact_limits_are_inclusive(self) -> None:
        collector = TelemetryCollector()
        for i in range(20):
            collector.record_request(250.0, ok=i != 0)

        slo = collector.evaluate_slo()
        self.assertEqual(slo["evaluated"], {"error_rate": 0.05, "average_latency_ms": 250.0})
        self.assertEqual(slo["status"], "pass")
        self.assertTrue(slo["passed"])


if __name__ == "__main__":
    unittest.main()
