from __future__ import annotations

from dataclasses import asdict, dataclass, field


class InvalidTransitionError(RuntimeError):
    """Raised when an event is not allowed from the current state."""


class WorkflowTimeoutError(RuntimeError):
    """Raised when a workflow is already expired before the requested event."""


@dataclass(frozen=True)
class WorkflowConfig:
    name: str
    timeout_step: int = 3


@dataclass
class TransitionRecord:
    event: str
    from_state: str
    to_state: str
    operator: str
    reason: str


@dataclass
class WorkflowInstance:
    workflow_id: str
    state: str = "draft"
    step: int = 0
    payload_ready: bool = False
    history: list[TransitionRecord] = field(default_factory=list)
    manual_review_reason: str | None = None
    compensation_count: int = 0


class WorkflowEngine:
    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config
        self._rules: dict[tuple[str, str], str] = {
            ("draft", "validate"): "validated",
            ("validated", "approve"): "approved",
            ("validated", "reject"): "manual_review",
            ("approved", "execute_success"): "completed",
            ("approved", "execute_fail"): "failed",
            ("failed", "compensate"): "compensated",
            ("expired", "manual_review"): "manual_review",
        }

    def start(self, workflow_id: str, *, payload_ready: bool = False) -> WorkflowInstance:
        return WorkflowInstance(workflow_id=workflow_id, payload_ready=payload_ready)

    def apply(
        self,
        instance: WorkflowInstance,
        event: str,
        *,
        operator: str,
        reason: str = "",
        step_increment: int = 1,
    ) -> WorkflowInstance:
        if instance.state == "expired":
            raise WorkflowTimeoutError(f"workflow {instance.workflow_id} already expired")
        if event == "approve" and not instance.payload_ready:
            raise InvalidTransitionError("payload is not ready for approval")

        target = self._rules.get((instance.state, event))
        if target is None:
            raise InvalidTransitionError(f"event {event} is not allowed from {instance.state}")

        old_state = instance.state
        instance.state = target
        instance.step += step_increment
        if target == "manual_review":
            instance.manual_review_reason = reason or event
        if event == "compensate":
            instance.compensation_count += 1
        instance.history.append(
            TransitionRecord(
                event=event,
                from_state=old_state,
                to_state=target,
                operator=operator,
                reason=reason or event,
            )
        )
        return instance

    def enforce_timeout(self, instance: WorkflowInstance, *, operator: str, reason: str) -> WorkflowInstance:
        if instance.state in {"completed", "compensated", "manual_review"}:
            return instance
        if instance.step < self.config.timeout_step:
            return instance
        old_state = instance.state
        instance.state = "expired"
        instance.manual_review_reason = reason
        instance.history.append(
            TransitionRecord(
                event="timeout",
                from_state=old_state,
                to_state="expired",
                operator=operator,
                reason=reason,
            )
        )
        return instance

    def audit_report(self, instance: WorkflowInstance) -> dict[str, object]:
        return {
            "workflow_name": self.config.name,
            "workflow_id": instance.workflow_id,
            "state": instance.state,
            "step": instance.step,
            "payload_ready": instance.payload_ready,
            "manual_review_reason": instance.manual_review_reason,
            "compensation_count": instance.compensation_count,
            "history": [asdict(record) for record in instance.history],
        }
