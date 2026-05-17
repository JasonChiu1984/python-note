from __future__ import annotations

import unittest

from workflow_state_machine_engineering.engine import InvalidTransitionError, WorkflowConfig, WorkflowEngine, WorkflowTimeoutError


class WorkflowStateMachineEngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = WorkflowEngine(WorkflowConfig(name="device-approval", timeout_step=2))

    def test_happy_path_reaches_completed(self) -> None:
        flow = self.engine.start("wf-001", payload_ready=True)
        self.engine.apply(flow, "validate", operator="qa")
        self.engine.apply(flow, "approve", operator="lead")
        self.engine.apply(flow, "execute_success", operator="runner")
        report = self.engine.audit_report(flow)
        self.assertEqual(report["state"], "completed")
        self.assertEqual(len(report["history"]), 3)

    def test_guard_blocks_approve_without_payload(self) -> None:
        flow = self.engine.start("wf-002", payload_ready=False)
        self.engine.apply(flow, "validate", operator="qa")
        with self.assertRaises(InvalidTransitionError):
            self.engine.apply(flow, "approve", operator="lead")

    def test_invalid_transition_is_rejected(self) -> None:
        flow = self.engine.start("wf-003", payload_ready=True)
        with self.assertRaises(InvalidTransitionError):
            self.engine.apply(flow, "execute_success", operator="runner")

    def test_failure_then_compensation_is_recorded(self) -> None:
        flow = self.engine.start("wf-004", payload_ready=True)
        self.engine.apply(flow, "validate", operator="qa")
        self.engine.apply(flow, "approve", operator="lead")
        self.engine.apply(flow, "execute_fail", operator="runner", reason="downstream rejected")
        self.engine.apply(flow, "compensate", operator="ops", reason="rollback side effect")
        report = self.engine.audit_report(flow)
        self.assertEqual(report["state"], "compensated")
        self.assertEqual(report["compensation_count"], 1)
        self.assertEqual(report["history"][-1]["event"], "compensate")

    def test_timeout_then_manual_review_handoff(self) -> None:
        flow = self.engine.start("wf-005", payload_ready=True)
        self.engine.apply(flow, "validate", operator="qa")
        self.engine.apply(flow, "approve", operator="lead")
        self.engine.enforce_timeout(flow, operator="system", reason="awaiting execution too long")
        report = self.engine.audit_report(flow)
        self.assertEqual(report["state"], "expired")
        with self.assertRaises(WorkflowTimeoutError):
            self.engine.apply(flow, "execute_success", operator="runner")


if __name__ == "__main__":
    unittest.main()
