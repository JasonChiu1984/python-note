from __future__ import annotations

import json

from batch_scheduler_engineering.runner import BatchJobRunner, JobConfig, SchedulerExecutionError


def main() -> None:
    runner = BatchJobRunner()
    job = JobConfig(
        name="nightly-reconciliation",
        owner="team-ops",
        schedule="0 2 * * *",
        checkpoint_key="reconcile:last-item",
        max_attempts=3,
    )
    failures: dict[int, int] = {2: 1, 5: 3}

    def handler(item: int) -> None:
        remaining = failures.get(item, 0)
        if remaining:
            failures[item] = remaining - 1
            raise SchedulerExecutionError(f"transient failure on item {item}")

    first = runner.run_job(job, [0, 1, 2, 3], "worker-a", handler)
    second = runner.run_job(job, [0, 1, 2, 3, 4, 5], "worker-a", handler)
    backfill = runner.run_job(job, [1, 2, 3], "worker-b", lambda item: None, backfill_from=1)
    print(json.dumps({"first": first, "second": second, "backfill": backfill}, ensure_ascii=False, indent=2))
    if second["dead_letter_count"] != 1 or backfill["backfill_mode"] is not True:
        raise SystemExit("batch scheduler smoke failed")
    print("batch scheduler smoke passed: lease + checkpoint + retry + dead-letter + backfill")


if __name__ == "__main__":
    main()
