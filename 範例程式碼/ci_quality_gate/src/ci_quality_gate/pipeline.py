from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .checks import CheckResult


@dataclass(frozen=True)
class CIJob:
    name: str
    run: Callable[[], CheckResult]
    blocking: bool = True


class Pipeline:
    def __init__(self, jobs: Iterable[CIJob]) -> None:
        self._jobs = tuple(jobs)

    def run(self) -> tuple[CheckResult, ...]:
        results: list[CheckResult] = []
        for job in self._jobs:
            result = job.run()
            if result.blocking != job.blocking:
                result = CheckResult(result.name, result.passed, result.detail, job.blocking)
            results.append(result)
            if job.blocking and not result.passed:
                break
        return tuple(results)
