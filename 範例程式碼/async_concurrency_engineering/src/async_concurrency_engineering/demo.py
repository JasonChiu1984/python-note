"""Demo command for the async worker pipeline sample."""

from __future__ import annotations

import asyncio

from .pipeline import RetryableJobError, WorkItem, run_pipeline


async def demo_handler(item: WorkItem) -> int:
    await asyncio.sleep(0.01)
    if item.payload == 13 and not item.idempotency_key.endswith(":retried"):
        raise RetryableJobError("upstream busy")
    return item.payload * 2


async def main() -> None:
    items = [
        WorkItem("job-1", 10, "job-1"),
        WorkItem("job-2", 13, "job-2:retried"),
        WorkItem("job-3", 21, "job-3"),
    ]
    results, metrics = await run_pipeline(items, demo_handler, worker_count=2)
    print({"results": [result.status for result in results], "submitted": metrics.submitted, "succeeded": metrics.succeeded})


if __name__ == "__main__":
    asyncio.run(main())
