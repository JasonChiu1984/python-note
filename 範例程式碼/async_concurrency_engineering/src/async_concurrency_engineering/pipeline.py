"""Bounded, in-memory asyncio worker pipeline for Python 3.11+."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar


class RetryableJobError(Exception):
    """Retry only when the operation's contract permits it."""


class PermanentJobError(Exception):
    """Repetition would not fix this job."""


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
    duration_ms: float = 0.0  # Includes queue wait, not merely handler runtime.


@dataclass
class AsyncPipelineMetrics:
    submitted: int = 0
    succeeded: int = 0
    failed: int = 0
    timed_out: int = 0  # Terminal timed-out jobs, a subset of failed.
    attempt_timeouts: int = 0
    retried: int = 0   # Additional attempts that actually started.
    cancelled: int = 0  # Started jobs cancelled during abort.


@dataclass(frozen=True)
class _Envelope:
    item: WorkItem
    started: float
    deadline: float


Handler = Callable[[WorkItem], Awaitable[int]]
T = TypeVar("T")


class AsyncWorkerPipeline:
    """Single-event-loop owner; stop and await producers before close() or abort()."""

    def __init__(
        self,
        handler: Handler,
        *,
        worker_count: int = 3,
        max_queue_size: int = 8,
        per_item_timeout: float = 0.25,
        max_attempts: int = 2,
        admission_timeout: float = 1.0,
        job_timeout: float = 2.0,
        retry_delay: float = 0.02,
        drain_timeout: float = 5.0,
    ) -> None:
        if min(worker_count, max_queue_size, max_attempts) < 1:
            raise ValueError("worker count, queue size and attempts must be positive")
        budgets = (per_item_timeout, admission_timeout, job_timeout, drain_timeout)
        if not all(math.isfinite(x) and x > 0 for x in budgets):
            raise ValueError("time budgets must be finite and positive")
        if not math.isfinite(retry_delay) or retry_delay < 0:
            raise ValueError("retry_delay must be finite and non-negative")
        self._handler = handler
        self._worker_count = worker_count
        self._queue: asyncio.Queue[_Envelope | None] = asyncio.Queue(maxsize=max_queue_size)
        self._per_item_timeout = per_item_timeout
        self._max_attempts = max_attempts
        self._admission_timeout = admission_timeout
        self._job_timeout = job_timeout
        self._retry_delay = retry_delay
        self._drain_timeout = drain_timeout
        self._workers: list[asyncio.Task[None]] = []
        self._accepting = True
        self._submitters = 0
        self._closed = False
        self._closing_lock = asyncio.Lock()
        self.metrics = AsyncPipelineMetrics()
        self.results: list[JobResult] = []  # Finite demo only: use a result sink for long-running services.

    async def start(self) -> None:
        if not self._accepting:
            raise RuntimeError("pipeline is closed")
        if not self._workers:
            self._workers = [
                asyncio.create_task(self._worker_loop(), name=f"async-worker-{index}")
                for index in range(self._worker_count)
            ]

    async def _supervise(self, operation: Awaitable[T]) -> T:
        """Watch worker failure while waiting on admission or drain."""
        waiting = asyncio.ensure_future(operation)
        try:
            await asyncio.wait([waiting, *self._workers], return_when=asyncio.FIRST_COMPLETED)
            for worker in self._workers:
                if worker.done():
                    worker.result()  # Re-raise the real failure.
                    raise RuntimeError("worker stopped before draining")
            return waiting.result()
        finally:
            if not waiting.done():
                waiting.cancel()
            await asyncio.gather(waiting, return_exceptions=True)

    async def submit(self, item: WorkItem) -> None:
        if not self._workers or not self._accepting:
            raise RuntimeError("pipeline is not accepting submissions")
        now = asyncio.get_running_loop().time()
        envelope = _Envelope(item, now, now + self._job_timeout)
        self._submitters += 1
        try:
            async with asyncio.timeout(min(self._admission_timeout, self._job_timeout)):
                await self._supervise(self._enqueue(envelope))
        finally:
            self._submitters -= 1

    async def _enqueue(self, envelope: _Envelope) -> None:
        await self._queue.put(envelope)
        self.metrics.submitted += 1  # Admission is counted at the actual queue boundary.

    async def close(self) -> None:
        async with self._closing_lock:
            if self._closed:
                return
            if self._submitters:
                raise RuntimeError("stop and await producers before closing")
            self._accepting = False
            try:
                async with asyncio.timeout(self._drain_timeout):
                    if self._workers:
                        await self._supervise(self._queue.join())
                        for _ in self._workers:
                            await self._queue.put(None)
                        await asyncio.gather(*self._workers)
                self._closed = True
            except BaseException:
                await self.abort()
                raise

    async def abort(self) -> None:
        """Cancel workers, await their cleanup, and discard in-memory backlog."""
        self._accepting = False
        for worker in self._workers:
            if not worker.done():
                worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()
        self._closed = True

    async def _worker_loop(self) -> None:
        while True:
            envelope = await self._queue.get()
            try:
                if envelope is None:
                    return
                self.results.append(await self._handle_with_retry(envelope))
            finally:
                self._queue.task_done()

    async def _handle_with_retry(self, envelope: _Envelope) -> JobResult:
        clock = asyncio.get_running_loop().time
        item = envelope.item
        attempts = 0
        last_status, last_error = "timed_out", "job deadline expired"
        try:
            while attempts < self._max_attempts:
                remaining = envelope.deadline - clock()
                if remaining <= 0:
                    last_status, last_error = "timed_out", "job deadline expired"
                    break
                attempts += 1
                if attempts > 1:
                    self.metrics.retried += 1
                try:
                    async with asyncio.timeout(min(remaining, self._per_item_timeout)):
                        value = await self._handler(item)
                    self.metrics.succeeded += 1
                    return JobResult(item.item_id, "succeeded", attempts, value=value,
                                     duration_ms=round((clock() - envelope.started) * 1000, 3))
                except TimeoutError:
                    self.metrics.attempt_timeouts += 1
                    last_status, last_error = "timed_out", "timeout"
                except RetryableJobError as exc:
                    last_status, last_error = "failed", str(exc)
                except PermanentJobError as exc:
                    last_status, last_error = "failed", str(exc)
                    break
                if attempts < self._max_attempts:
                    delay = min(self._retry_delay * 2 ** min(attempts - 1, 10), 1.0)
                    await asyncio.sleep(min(delay, max(0, envelope.deadline - clock())))
        except asyncio.CancelledError:
            self.metrics.cancelled += 1
            raise
        self.metrics.failed += 1
        if last_status == "timed_out":
            self.metrics.timed_out += 1
        return JobResult(item.item_id, last_status, attempts, error=last_error,
                         duration_ms=round((clock() - envelope.started) * 1000, 3))


async def run_pipeline(
    items: Iterable[WorkItem],
    handler: Handler,
    *,
    worker_count: int = 3,
    max_queue_size: int = 8,
    per_item_timeout: float = 0.25,
    max_attempts: int = 2,
    admission_timeout: float = 1.0,
    job_timeout: float = 2.0,
    retry_delay: float = 0.02,
    drain_timeout: float = 5.0,
) -> tuple[list[JobResult], AsyncPipelineMetrics]:
    pipeline = AsyncWorkerPipeline(
        handler, worker_count=worker_count, max_queue_size=max_queue_size,
        per_item_timeout=per_item_timeout, max_attempts=max_attempts,
        admission_timeout=admission_timeout, job_timeout=job_timeout,
        retry_delay=retry_delay, drain_timeout=drain_timeout,
    )
    await pipeline.start()
    try:
        for item in items:
            await pipeline.submit(item)
        await pipeline.close()
    except BaseException:
        await pipeline.abort()
        raise
    return pipeline.results, pipeline.metrics
