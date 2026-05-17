from __future__ import annotations

from workflow_state_machine_engineering.engine import WorkflowConfig, WorkflowEngine


def main() -> None:
    engine = WorkflowEngine(WorkflowConfig(name="device-approval", timeout_step=2))

    success = engine.start("wf-success", payload_ready=True)
    engine.apply(success, "validate", operator="qa")
    engine.apply(success, "approve", operator="lead")
    engine.apply(success, "execute_success", operator="runner")

    failed = engine.start("wf-failure", payload_ready=True)
    engine.apply(failed, "validate", operator="qa")
    engine.apply(failed, "approve", operator="lead")
    engine.apply(failed, "execute_fail", operator="runner", reason="device busy")
    engine.apply(failed, "compensate", operator="ops", reason="revert reservation")

    delayed = engine.start("wf-delay", payload_ready=True)
    engine.apply(delayed, "validate", operator="qa")
    engine.apply(delayed, "approve", operator="lead")
    engine.enforce_timeout(delayed, operator="system", reason="deadline exceeded")

    completed = engine.audit_report(success)
    compensated = engine.audit_report(failed)
    expired = engine.audit_report(delayed)
    assert completed["state"] == "completed"
    assert compensated["state"] == "compensated"
    assert expired["state"] == "expired"
    print("workflow state machine smoke passed: transition + compensation + timeout + audit")


if __name__ == "__main__":
    main()
