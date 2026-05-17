from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Iterable


PINNED_RE = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.!+-]+$")


class GovernanceError(ValueError):
    """Raised when dependency governance rules are violated."""


@dataclass(frozen=True)
class RuntimePolicy:
    minimum_python: tuple[int, int]
    recommended_python: tuple[int, int]
    preview_python: str
    requires_venv: bool


DEFAULT_RUNTIME_POLICY = RuntimePolicy(
    minimum_python=(3, 11),
    recommended_python=(3, 14),
    preview_python="3.15.0b1",
    requires_venv=False,
)


def _read_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _parse_requirement_names(lines: Iterable[str]) -> list[str]:
    names: list[str] = []
    for line in lines:
        if line.startswith("-r "):
            continue
        name = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()
        if not name:
            raise GovernanceError(f"Invalid requirement line: {line}")
        names.append(name)
    return names


def _ensure_pinned(lines: Iterable[str]) -> None:
    for line in lines:
        if line.startswith("-r "):
            continue
        if not PINNED_RE.match(line):
            raise GovernanceError(f"Dependency is not pinned: {line}")


def evaluate_governance(base_dir: Path, runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY) -> dict:
    requirements = _read_lines(base_dir / "requirements.txt")
    requirements_dev = _read_lines(base_dir / "requirements-dev.txt")
    constraints = _read_lines(base_dir / "constraints.txt")

    _ensure_pinned(requirements)
    _ensure_pinned(requirements_dev)
    _ensure_pinned(constraints)

    if not requirements_dev or requirements_dev[0] != "-r requirements.txt":
        raise GovernanceError("requirements-dev.txt must start with '-r requirements.txt'")

    prod_names = _parse_requirement_names(requirements)
    dev_names = _parse_requirement_names(requirements_dev)
    constraint_names = set(_parse_requirement_names(constraints))

    missing_constraints = sorted((set(prod_names) | set(dev_names)) - constraint_names)
    if missing_constraints:
        raise GovernanceError(
            f"constraints.txt is missing pinned packages: {', '.join(missing_constraints)}"
        )

    python_runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    runtime_ok = (sys.version_info.major, sys.version_info.minor) >= runtime_policy.minimum_python
    if not runtime_ok:
        raise GovernanceError(
            f"Python {python_runtime} is below minimum {runtime_policy.minimum_python[0]}.{runtime_policy.minimum_python[1]}"
        )

    return {
        "runtime": {
            "current": python_runtime,
            "minimum": ".".join(map(str, runtime_policy.minimum_python)),
            "recommended": ".".join(map(str, runtime_policy.recommended_python)),
            "preview": runtime_policy.preview_python,
            "venv_active": sys.prefix != getattr(sys, "base_prefix", sys.prefix),
            "runtime_ok": runtime_ok,
        },
        "dependency_policy": {
            "requirements_count": len(requirements),
            "requirements_dev_count": len(requirements_dev),
            "constraints_count": len(constraints),
            "prod_dependencies": prod_names,
            "dev_dependencies": dev_names,
        },
        "evidence": {
            "startup_command": "PYTHONPATH=src python3 -m unittest discover -s tests -v",
            "smoke_command": "PYTHONPATH=src python3 scripts/run_dependency_environment_governance_smoke.py",
            "governance_passed": True,
        },
    }


def render_report(base_dir: Path, output_path: Path) -> Path:
    report = evaluate_governance(base_dir)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
