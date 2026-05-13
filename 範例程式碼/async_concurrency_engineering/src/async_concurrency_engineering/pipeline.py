"""Bounded asyncio worker pipeline used by the tutorial."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass


class RetryableJobError(Exception):
    """Raised when a job can be retried safely."""


class PermanentJobError(Exception):
    """Raised when retrying would not fix the job."""


@dataclass(frozen=True)
class WorkItem:
    item_id: str
    payload: int
    idempotency_key: str


@dataclass(frozen=True)
class JobResult:
    item_id: str
    status: str
    attempts: int
    value: int | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class AsyncPipelineMetrics:
    submitted: int = 0
    succeeded: int = 0
    failed: int = 0
    timed_out: int = 0
    retried: int = 0
    cancelled: int = 0


Handler = Callable[[WorkItem], Awaitable[int]]


class AsyncWorkerPipeline:
    def __init__(
        self,
        handler: Handler,
        *,
        worker_count: int = 3,
        max_queue_size: int = 8,
        per_item_timeout: float = 0.25,
        max_attempts: int = 2,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be >= 1")
        if per_item_timeout <= 0:
            raise ValueError("per_item_timeout must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._handler = handler
        self._worker_count = worker_count
        self._queue: asyncio.Queue[WorkItem | None] = asyncio.Queue(maxsize=max_queue_size)
        self._per_item_timeout = per_item_timeout
        self._max_attempts = max_attempts
        self._workers: list[asyncio.Task[None]] = []
        self._accepting = True
        self.metrics = AsyncPipelineMetrics()
        self.results: list[JobResult] = []

    async def start(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._worker_loop(worker_id), name=f"async-worker-{worker_id}")
            for worker_id in range(self._worker_count)
        ]

    async def submit(self, item: WorkItem) -> None:
        if not self._workers:
            raise RuntimeError("pipeline must be started before submit")
        if not self._accepting:
            raise RuntimeError("pipeline is closed for new submissions")
        await self._queue.put(item)
        self.metrics.submitted += 1

    async def close(self) -> None:
        self._accepting = False
        await self._queue.join()
        for _ in self._workers:
            await self._queue.put(None)
        if self._workers:
            await asyncio.gather(*self._workers)

    async def _worker_loop(self, worker_id: int) -> None:
        while True:
            item = await self._queue.get()
            try:
                if item is None:
                    return
                result = await self._handle_with_retry(item)
                self.results.append(result)
            finally:
                self._queue.task_done()

    async def _handle_with_retry(self, item: WorkItem) -> JobResult:
        started = time.perf_counter()
        attempts = 0
        while attempts < self._max_attempts:
            attempts += 1
            try:
                value = await asyncio.wait_for(self._handler(item), timeout=self._per_item_timeout)
                self.metrics.succeeded += 1
                return JobResult(
                    item_id=item.item_id,
                    status="succeeded",
                    attempts=attempts,
                    value=value,
                    duration_ms=_elapsed_ms(started),
                )
            except asyncio.TimeoutError:
                self.metrics.timed_out += 1
                if attempts >= self._max_attempts:
                    self.metrics.failed += 1
                    return JobResult(item.item_id, "timed_out", attempts, error="timeout", duration_ms=_elapsed_ms(started))
                self.metrics.retried += 1
            except RetryableJobError as exc:
                if attempts >= self._max_attempts:
                    self.metrics.failed += 1
                    return JobResult(item.item_id, "failed", attempts, error=str(exc), duration_ms=_elapsed_ms(started))
                self.metrics.retried += 1
            except PermanentJobError as exc:
                self.metrics.failed += 1
                return JobResult(item.item_id, "failed", attempts, error=str(exc), duration_ms=_elapsed_ms(started))
            except asyncio.CancelledError:
                self.metrics.cancelled += 1
                raise
        self.metrics.failed += 1
        return JobResult(item.item_id, "failed", attempts, error="max attempts reached", duration_ms=_elapsed_ms(started))


async def run_pipeline(
    items: Iterable[WorkItem],
    handler: Handler,
    *,
    worker_count: int = 3,
    max_queue_size: int = 8,
    per_item_timeout: float = 0.25,
    max_attempts: int = 2,
) -> tuple[list[JobResult], AsyncPipelineMetrics]:
    pipeline = AsyncWorkerPipeline(
        handler,
        worker_count=worker_count,
        max_queue_size=max_queue_size,
        per_item_timeout=per_item_timeout,
        max_attempts=max_attempts,
    )
    await pipeline.start()
    for item in items:
        await pipeline.submit(item)
    await pipeline.close()
    return pipeline.results, pipeline.metrics


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
