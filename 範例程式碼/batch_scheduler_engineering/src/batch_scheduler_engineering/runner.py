from __future__ import annotations

from dataclasses import asdict, dataclass


class SchedulerExecutionError(RuntimeError):
    """Raised when a single batch item fails."""


class LeaseConflictError(RuntimeError):
    """Raised when another worker already owns the job lease."""


@dataclass(frozen=True)
class JobConfig:
    name: str
    owner: str
    schedule: str
    checkpoint_key: str
    max_attempts: int = 3


@dataclass
class SchedulerReport:
    job_name: str
    owner: str
    schedule: str
    worker_id: str
    processed: int = 0
    retries: int = 0
    dead_letter_count: int = 0
    last_checkpoint: int = -1
    backfill_mode: bool = False


class BatchJobRunner:
    def __init__(self) -> None:
        self._leases: dict[str, str] = {}
        self._checkpoints: dict[str, int] = {}
        self._dead_letters: list[dict[str, object]] = []

    def acquire_lease(self, job: JobConfig, worker_id: str) -> None:
        current = self._leases.get(job.name)
        if current and current != worker_id:
            raise LeaseConflictError(f"job {job.name} is already leased by {current}")
        self._leases[job.name] = worker_id

    def release_lease(self, job: JobConfig, worker_id: str) -> None:
        if self._leases.get(job.name) == worker_id:
            self._leases.pop(job.name, None)

    def get_checkpoint(self, job: JobConfig) -> int:
        return self._checkpoints.get(job.checkpoint_key, -1)

    def dead_letters(self) -> list[dict[str, object]]:
        return list(self._dead_letters)

    def run_job(
        self,
        job: JobConfig,
        items: list[int],
        worker_id: str,
        handler,
        *,
        backfill_from: int | None = None,
    ) -> dict[str, object]:
        self.acquire_lease(job, worker_id)
        report = SchedulerReport(
            job_name=job.name,
            owner=job.owner,
            schedule=job.schedule,
            worker_id=worker_id,
            last_checkpoint=self.get_checkpoint(job),
            backfill_mode=backfill_from is not None,
        )
        start_from = backfill_from if backfill_from is not None else self.get_checkpoint(job) + 1
        try:
            for item in items:
                if item < start_from:
                    continue
                self._handle_item(job, item, handler, report)
        finally:
            self.release_lease(job, worker_id)
        result = asdict(report)
        result["dead_letters"] = self.dead_letters()
        return result

    def _handle_item(self, job: JobConfig, item: int, handler, report: SchedulerReport) -> None:
        attempts = 0
        while attempts < job.max_attempts:
            attempts += 1
            try:
                handler(item)
                report.processed += 1
                report.last_checkpoint = item
                self._checkpoints[job.checkpoint_key] = item
                return
            except SchedulerExecutionError as exc:
                if attempts < job.max_attempts:
                    report.retries += 1
                    continue
                self._dead_letters.append(
                    {
                        "job_name": job.name,
                        "item": item,
                        "attempts": attempts,
                        "reason": str(exc),
                    }
                )
                report.dead_letter_count = len(self._dead_letters)
                return
