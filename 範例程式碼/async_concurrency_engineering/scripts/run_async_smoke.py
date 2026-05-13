#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from async_concurrency_engineering import RetryableJobError, WorkItem, run_pipeline


async def handler(item: WorkItem) -> int:
    await asyncio.sleep(0.005)
    if item.payload == 7:
        raise RetryableJobError("retryable smoke failure")
    return item.payload * 3


async def main() -> None:
    attempts: dict[str, int] = {}

    async def smoke_handler(item: WorkItem) -> int:
        attempts[item.item_id] = attempts.get(item.item_id, 0) + 1
        if attempts[item.item_id] == 1 and item.payload == 7:
            raise RetryableJobError("dependency busy")
        return await handler(WorkItem(item.item_id, 8 if item.payload == 7 else item.payload, item.idempotency_key))

    items = [
        WorkItem("a", 2, "a"),
        WorkItem("b", 7, "b"),
        WorkItem("c", 5, "c"),
    ]
    results, metrics = await run_pipeline(items, smoke_handler, worker_count=2, max_attempts=2)
    if metrics.submitted != 3 or metrics.succeeded != 3 or metrics.retried != 1:
        raise SystemExit(f"unexpected metrics: {metrics}")
    if sorted(result.value for result in results) != [6, 15, 24]:
        raise SystemExit(f"unexpected results: {results}")
    print("async smoke passed: bounded workers + retry + metrics")


if __name__ == "__main__":
    asyncio.run(main())
