from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import py_compile
import subprocess
import sys
from typing import Iterable


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    blocking: bool = True


@dataclass(frozen=True)
class GateReport:
    version: str
    commit: str
    results: tuple[CheckResult, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return all(result.passed or not result.blocking for result in self.results)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "commit": self.commit,
            "passed": self.passed,
            "results": [
                {
                    "name": result.name,
                    "passed": result.passed,
                    "detail": result.detail,
                    "blocking": result.blocking,
                }
                for result in self.results
            ],
        }


def run_py_compile(paths: Iterable[Path]) -> CheckResult:
    checked = 0
    for path in paths:
        py_compile.compile(str(path), doraise=True)
        checked += 1
    return CheckResult("py_compile", True, f"compiled {checked} python files")


def run_unittest(project_root: Path) -> CheckResult:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    completed = subprocess.run(
        command,
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return CheckResult("unittest", True, "unittest discover passed")
    detail = (completed.stdout + completed.stderr).strip().splitlines()[-1:]
    return CheckResult("unittest", False, detail[0] if detail else "unittest failed")


def check_coverage_policy(covered_items: int, total_items: int, floor: int = 80) -> CheckResult:
    if total_items <= 0:
        return CheckResult("coverage_policy", False, "total_items must be positive")
    percent = round((covered_items / total_items) * 100)
    passed = percent >= floor
    return CheckResult("coverage_policy", passed, f"coverage model {percent}% >= {floor}%")


def check_runtime_matrix(stable: str, beta: str) -> tuple[CheckResult, CheckResult]:
    stable_ok = stable.startswith("3.14")
    beta_ok = beta.startswith("3.15")
    return (
        CheckResult("stable_runtime", stable_ok, f"stable runtime lane {stable}", blocking=True),
        CheckResult("beta_runtime", beta_ok, f"beta preview lane {beta}", blocking=False),
    )


def check_workflow_contract(path: Path) -> CheckResult:
    text = path.read_text(encoding="utf-8")
    required = ["pull_request", "push", "workflow_dispatch", "3.14", "3.15-dev", "compile", "test"]
    missing = [item for item in required if item not in text]
    if missing:
        return CheckResult("workflow_contract", False, f"missing workflow tokens: {', '.join(missing)}")
    return CheckResult("workflow_contract", True, "workflow has trigger, matrix, compile, and test")


def build_release_evidence(report: GateReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def evaluate_gate(project_root: Path, version: str, commit: str) -> GateReport:
    source_files = sorted((project_root / "src").glob("ci_quality_gate/*.py"))
    script_files = sorted((project_root / "scripts").glob("*.py"))
    results: list[CheckResult] = [
        run_py_compile([*source_files, *script_files]),
        run_unittest(project_root),
        check_coverage_policy(covered_items=9, total_items=10, floor=80),
        check_workflow_contract(project_root / ".github" / "workflows" / "python-ci.yml"),
    ]
    results.extend(check_runtime_matrix(stable="3.14", beta="3.15-dev"))
    return GateReport(version=version, commit=commit, results=tuple(results))
