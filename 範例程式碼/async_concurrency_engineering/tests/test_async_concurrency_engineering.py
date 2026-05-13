from __future__ import annotations

import asyncio
import unittest

from async_concurrency_engineering import AsyncWorkerPipeline, RetryableJobError, WorkItem, run_pipeline


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


if __name__ == "__main__":
    unittest.main()
