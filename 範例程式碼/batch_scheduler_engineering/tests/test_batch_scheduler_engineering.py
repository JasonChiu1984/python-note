from __future__ import annotations

import unittest

from batch_scheduler_engineering.runner import BatchJobRunner, JobConfig, LeaseConflictError, SchedulerExecutionError


class BatchSchedulerEngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = BatchJobRunner()
        self.job = JobConfig(
            name="nightly-reconciliation",
            owner="team-ops",
            schedule="0 2 * * *",
            checkpoint_key="reconcile:last-item",
            max_attempts=3,
        )

    def test_checkpoint_resume_skips_completed_items(self) -> None:
        seen: list[int] = []
        self.runner.run_job(self.job, [0, 1, 2], "worker-a", lambda item: seen.append(item))
        self.runner.run_job(self.job, [0, 1, 2, 3, 4], "worker-a", lambda item: seen.append(item))
        self.assertEqual(seen, [0, 1, 2, 3, 4])

    def test_lease_conflict_is_rejected(self) -> None:
        self.runner.acquire_lease(self.job, "worker-a")
        with self.assertRaises(LeaseConflictError):
            self.runner.acquire_lease(self.job, "worker-b")

    def test_retry_then_success_updates_checkpoint(self) -> None:
        attempts = {2: 1}

        def flaky(item: int) -> None:
            remaining = attempts.get(item, 0)
            if remaining:
                attempts[item] = remaining - 1
                raise SchedulerExecutionError("retryable")

        report = self.runner.run_job(self.job, [0, 1, 2], "worker-a", flaky)
        self.assertEqual(report["processed"], 3)
        self.assertEqual(report["retries"], 1)
        self.assertEqual(report["last_checkpoint"], 2)

    def test_dead_letter_after_retry_budget(self) -> None:
        def broken(_: int) -> None:
            raise SchedulerExecutionError("broken item")

        report = self.runner.run_job(self.job, [5], "worker-a", broken)
        self.assertEqual(report["dead_letter_count"], 1)
        self.assertEqual(report["dead_letters"][0]["item"], 5)

    def test_backfill_mode_reprocesses_window(self) -> None:
        seen: list[int] = []
        self.runner.run_job(self.job, [0, 1, 2], "worker-a", lambda item: seen.append(item))
        report = self.runner.run_job(self.job, [1, 2], "worker-b", lambda item: seen.append(item), backfill_from=1)
        self.assertTrue(report["backfill_mode"])
        self.assertEqual(seen, [0, 1, 2, 1, 2])
