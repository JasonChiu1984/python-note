from __future__ import annotations

import asyncio
import unittest

from async_concurrency_engineering import AsyncWorkerPipeline, PermanentJobError, RetryableJobError, WorkItem, run_pipeline


class AsyncWorkerPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_processes_items_with_bounded_workers(self) -> None:
        async def handler(item: WorkItem) -> int:
            await asyncio.sleep(0)
            return item.payload * 10

        items = [WorkItem(f"job-{index}", index, f"key-{index}") for index in range(5)]
        results, metrics = await run_pipeline(items, handler, worker_count=2)

        self.assertEqual(metrics.submitted, 5)
        self.assertEqual(metrics.succeeded, 5)
        self.assertEqual(sorted(result.value for result in results), [0, 10, 20, 30, 40])

    async def test_retries_retryable_error(self) -> None:
        calls: dict[str, int] = {}

        async def handler(item: WorkItem) -> int:
            calls[item.item_id] = calls.get(item.item_id, 0) + 1
            if calls[item.item_id] == 1:
                raise RetryableJobError("temporary dependency failure")
            return item.payload + 1

        results, metrics = await run_pipeline([WorkItem("retry", 41, "retry-key")], handler, max_attempts=2)

        self.assertEqual(results[0].status, "succeeded")
        self.assertEqual(results[0].attempts, 2)
        self.assertEqual(results[0].value, 42)
        self.assertEqual(metrics.retried, 1)

    async def test_timeout_is_classified(self) -> None:
        async def slow_handler(item: WorkItem) -> int:
            await asyncio.sleep(0.05)
            return item.payload

        results, metrics = await run_pipeline(
            [WorkItem("slow", 1, "slow-key")],
            slow_handler,
            per_item_timeout=0.001,
            max_attempts=1,
        )

        self.assertEqual(results[0].status, "timed_out")
        self.assertEqual(metrics.timed_out, 1)
        self.assertEqual(metrics.failed, 1)

    async def test_queue_maxsize_creates_backpressure(self) -> None:
        release_worker = asyncio.Event()

        async def handler(item: WorkItem) -> int:
            await release_worker.wait()
            return item.payload

        pipeline = AsyncWorkerPipeline(handler, worker_count=1, max_queue_size=1)
        await pipeline.start()
        await pipeline.submit(WorkItem("first", 1, "first"))
        await asyncio.sleep(0)
        await pipeline.submit(WorkItem("second", 2, "second"))

        second_submit = asyncio.create_task(pipeline.submit(WorkItem("third", 3, "third")))
        await asyncio.sleep(0.01)

        self.assertFalse(second_submit.done())
        second_submit.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await second_submit
        release_worker.set()
        await pipeline.close()

    async def test_close_drains_queue_and_stops_workers(self) -> None:
        async def handler(item: WorkItem) -> int:
            await asyncio.sleep(0)
            return item.payload

        pipeline = AsyncWorkerPipeline(handler, worker_count=2)
        await pipeline.start()
        await pipeline.submit(WorkItem("one", 1, "one"))
        await pipeline.submit(WorkItem("two", 2, "two"))
        await pipeline.close()

        self.assertEqual(len(pipeline.results), 2)
        self.assertTrue(all(worker.done() for worker in pipeline._workers))


    async def test_worker_failure_surfaces_while_admission_is_blocked(self) -> None:
        hit = asyncio.Event()
        release = asyncio.Event()

        async def handler(item: WorkItem) -> int:
            hit.set()
            await release.wait()
            raise LookupError("unexpected handler defect")

        p = AsyncWorkerPipeline(handler, worker_count=1, max_queue_size=1)
        await p.start()
        try:
            await p.submit(WorkItem("active", 1, "active"))
            await hit.wait()
            await p.submit(WorkItem("queued", 2, "queued"))
            blocked = asyncio.create_task(p.submit(WorkItem("blocked", 3, "blocked")))
            await asyncio.sleep(0)
            self.assertFalse(blocked.done())
            release.set()
            with self.assertRaisesRegex(LookupError, "unexpected handler defect"):
                await asyncio.wait_for(blocked, 1)
        finally:
            await p.abort()
        self.assertTrue(all(worker.done() for worker in p._workers))
        self.assertEqual(p.metrics.submitted, 2)

    async def test_worker_failure_surfaces_during_drain(self) -> None:
        async def handler(item: WorkItem) -> int:
            await asyncio.sleep(0)
            raise LookupError("broken worker")
        with self.assertRaisesRegex(LookupError, "broken worker"):
            await asyncio.wait_for(run_pipeline([WorkItem("x", 1, "x")], handler, worker_count=1), 1)

    async def test_permanent_error_never_retries(self) -> None:
        async def handler(item: WorkItem) -> int:
            raise PermanentJobError("invalid input")
        result, metrics = await run_pipeline([WorkItem("bad", 1, "bad")], handler, max_attempts=3)
        self.assertEqual((result[0].status, result[0].attempts, metrics.retried), ("failed", 1, 0))

    async def test_drain_timeout_cleans_worker_and_discards_backlog(self) -> None:
        active = asyncio.Event()
        cleaned = asyncio.Event()
        never = asyncio.Event()

        async def handler(item: WorkItem) -> int:
            active.set()
            try:
                await never.wait()
            finally:
                cleaned.set()
            return item.payload

        p = AsyncWorkerPipeline(handler, worker_count=1, max_queue_size=1,
                                drain_timeout=0.015, per_item_timeout=1)
        await p.start()
        await p.submit(WorkItem("active", 1, "active"))
        await active.wait()
        await p.submit(WorkItem("queued", 2, "queued"))
        with self.assertRaises(TimeoutError):
            await p.close()
        self.assertTrue(cleaned.is_set())
        self.assertTrue(p._queue.empty())
        self.assertEqual(p.metrics.cancelled, 1)
        await p.close()  # Idempotent after cleanup.

    async def test_total_job_budget_caps_retries(self) -> None:
        async def handler(item: WorkItem) -> int:
            raise RetryableJobError("busy")
        results, metrics = await run_pipeline(
            [WorkItem("budget", 1, "budget")], handler, max_attempts=9,
            job_timeout=0.04, retry_delay=1.0,
        )
        self.assertEqual((results[0].status, results[0].attempts), ("timed_out", 1))
        self.assertEqual((metrics.timed_out, metrics.retried), (1, 0))


if __name__ == "__main__":
    unittest.main()
