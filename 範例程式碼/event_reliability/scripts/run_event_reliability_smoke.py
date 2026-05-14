from __future__ import annotations

from pathlib import Path

from event_reliability.pipeline import EventPipeline, FakeBroker, IdempotentConsumer
from event_reliability.report import write_reliability_report
from event_reliability.testing import make_event


def build_handler() -> tuple[IdempotentConsumer, dict[str, int]]:
    state = {"calls": 0}

    def handler(envelope) -> None:
        state["calls"] += 1
        if envelope.payload.get("should_fail"):
            raise RuntimeError("poison payload")

    return IdempotentConsumer(handler), state


def main() -> None:
    consumer, state = build_handler()
    pipeline = EventPipeline(FakeBroker([False, True]), consumer, max_delivery_attempts=2)
    pipeline.enqueue_change(make_event("evt-1"))
    pipeline.dispatch_pending()
    pipeline.dispatch_pending()
    consumer.consume(pipeline.broker.published[0])

    poison_consumer, _ = build_handler()
    poison_pipeline = EventPipeline(FakeBroker(), poison_consumer, max_delivery_attempts=2)
    poison_pipeline.enqueue_change(make_event("evt-2", payload={"should_fail": True}))
    poison_pipeline.dispatch_pending()
    poison_pipeline.dispatch_pending()
    poison_consumer.handler = lambda envelope: None
    poison_pipeline.replay_dlq(0, "fixed handler")

    report_path = Path(__file__).resolve().parents[1] / "event_reliability_report.json"
    write_reliability_report(report_path, poison_pipeline)
    assert state["calls"] == 1
    assert poison_pipeline.report.replayed == 1
    print("event reliability smoke passed: outbox + dedup + dlq + replay + evidence")


if __name__ == "__main__":
    main()
