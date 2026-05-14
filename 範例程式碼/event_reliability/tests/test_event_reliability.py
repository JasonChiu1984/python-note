from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from event_reliability.pipeline import EventPipeline, FakeBroker, IdempotentConsumer
from event_reliability.report import write_reliability_report
from event_reliability.testing import make_event


class EventReliabilityTests(unittest.TestCase):
    def test_dispatch_retry_then_success(self) -> None:
        calls: list[str] = []

        def handler(envelope) -> None:
            calls.append(envelope.event_id)

        pipeline = EventPipeline(FakeBroker([False, True]), IdempotentConsumer(handler), max_delivery_attempts=3)
        pipeline.enqueue_change(make_event("evt-1"))
        pipeline.dispatch_pending()
        self.assertEqual(len(pipeline.store.pending), 1)
        pipeline.dispatch_pending()
        self.assertEqual(calls, ["evt-1"])
        self.assertEqual(pipeline.report.dispatched, 1)

    def test_duplicate_event_is_skipped(self) -> None:
        calls: list[str] = []

        def handler(envelope) -> None:
            calls.append(envelope.event_id)

        consumer = IdempotentConsumer(handler)
        event = make_event("evt-2")
        self.assertTrue(consumer.consume(EventPipeline(FakeBroker(), consumer)._to_envelope(event)))
        self.assertFalse(consumer.consume(EventPipeline(FakeBroker(), consumer)._to_envelope(event)))
        self.assertEqual(calls, ["evt-2"])
        self.assertEqual(consumer.duplicate_skips, 1)

    def test_poison_message_moves_to_dlq(self) -> None:
        def handler(envelope) -> None:
            raise RuntimeError("broken payload")

        pipeline = EventPipeline(FakeBroker(), IdempotentConsumer(handler), max_delivery_attempts=2)
        pipeline.enqueue_change(make_event("evt-3", payload={"should_fail": True}))
        pipeline.dispatch_pending()
        pipeline.dispatch_pending()
        self.assertEqual(len(pipeline.store.dlq), 1)
        self.assertEqual(pipeline.report.dlq_count, 1)

    def test_replay_after_fix_succeeds(self) -> None:
        def failing_handler(envelope) -> None:
            raise RuntimeError("still broken")

        consumer = IdempotentConsumer(failing_handler)
        pipeline = EventPipeline(FakeBroker(), consumer, max_delivery_attempts=1)
        pipeline.enqueue_change(make_event("evt-4"))
        pipeline.dispatch_pending()
        self.assertEqual(len(pipeline.store.dlq), 1)
        consumer.handler = lambda envelope: None
        pipeline.replay_dlq(0, "fixed handler")
        self.assertEqual(pipeline.report.replayed, 1)
        self.assertEqual(len(pipeline.store.dlq), 0)

    def test_order_is_preserved_by_handled_sequence(self) -> None:
        handled: list[str] = []

        def handler(envelope) -> None:
            handled.append(envelope.event_id)

        pipeline = EventPipeline(FakeBroker([True, True]), IdempotentConsumer(handler))
        pipeline.enqueue_change(make_event("evt-5", stream_key="line-1"))
        pipeline.enqueue_change(make_event("evt-6", stream_key="line-1"))
        pipeline.dispatch_pending()
        self.assertEqual(handled, ["evt-5", "evt-6"])

    def test_report_is_written(self) -> None:
        pipeline = EventPipeline(FakeBroker(), IdempotentConsumer(lambda envelope: None))
        pipeline.enqueue_change(make_event("evt-7"))
        pipeline.dispatch_pending()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "report.json"
            write_reliability_report(target, pipeline)
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["processed"], 1)
        self.assertEqual(payload["dlq_count"], 0)


if __name__ == "__main__":
    unittest.main()
