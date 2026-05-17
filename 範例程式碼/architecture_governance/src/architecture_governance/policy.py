from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class GovernanceError(ValueError):
    """Raised when architecture governance rules are violated."""


@dataclass(frozen=True)
class DeprecationEntry:
    component: str
    replacement: str
    sunset_date: str


@dataclass(frozen=True)
class GovernancePolicy:
    module_ownership: dict[str, str]
    import_rules: dict[str, list[str]]
    module_dependencies: dict[str, list[str]]
    deprecations: list[DeprecationEntry]


DEFAULT_MODULE_DEPENDENCIES = {
    "domain": [],
    "application": ["domain"],
    "adapters": ["application", "domain"],
    "interfaces": ["application", "domain"],
    "legacy_gateway": ["application"],
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_adr_blocks(path: Path) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
      line = raw_line.strip()
      if line.startswith("## ADR-"):
          if current:
              blocks.append(current)
          current = {"title": line[3:].strip()}
      elif current and line.startswith("- ") and ":" in line:
          key, value = line[2:].split(":", 1)
          current[key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


def load_policy(base_dir: Path) -> GovernancePolicy:
    ownership = _load_json(base_dir / "module_ownership.json")
    import_rules = _load_json(base_dir / "import_rules.json")
    deprecations = [
        DeprecationEntry(
            component="legacy_gateway.run",
            replacement="gateway_service.start",
            sunset_date="2026-08-31",
        )
    ]
    return GovernancePolicy(
        module_ownership=ownership,
        import_rules=import_rules,
        module_dependencies=DEFAULT_MODULE_DEPENDENCIES,
        deprecations=deprecations,
    )


def _validate_adr(path: Path) -> list[str]:
    issues: list[str] = []
    blocks = _parse_adr_blocks(path)
    if not blocks:
        raise GovernanceError("No ADR blocks found in architecture_decisions.md")
    required = {"context", "decision", "tradeoff", "replacement_trigger"}
    for block in blocks:
        missing = sorted(required - set(block))
        if missing:
            issues.append(f"{block.get('title', 'ADR')} missing fields: {', '.join(missing)}")
    return issues


def _validate_ownership(policy: GovernancePolicy) -> list[str]:
    issues: list[str] = []
    for module in policy.module_dependencies:
        if module not in policy.module_ownership:
            issues.append(f"Ownership missing for module: {module}")
    return issues


def _validate_import_rules(policy: GovernancePolicy) -> list[str]:
    issues: list[str] = []
    for module, deps in policy.module_dependencies.items():
        allowed = set(policy.import_rules.get(module, []))
        disallowed = sorted(dep for dep in deps if dep not in allowed)
        if disallowed:
            issues.append(
                f"Module {module} imports disallowed dependencies: {', '.join(disallowed)}"
            )
    return issues


def _validate_deprecations(policy: GovernancePolicy) -> list[str]:
    issues: list[str] = []
    for entry in policy.deprecations:
        if not entry.replacement:
            issues.append(f"Deprecation {entry.component} missing replacement")
        if not entry.sunset_date:
            issues.append(f"Deprecation {entry.component} missing sunset_date")
    return issues


def evaluate_governance(base_dir: Path) -> dict[str, Any]:
    policy = load_policy(base_dir)
    issues: list[str] = []
    issues.extend(_validate_adr(base_dir / "architecture_decisions.md"))
    issues.extend(_validate_ownership(policy))
    issues.extend(_validate_import_rules(policy))
    issues.extend(_validate_deprecations(policy))
    if issues:
        raise GovernanceError("; ".join(issues))
    return {
        "ownership": policy.module_ownership,
        "import_rules": policy.import_rules,
        "deprecations": [
            {
                "component": entry.component,
                "replacement": entry.replacement,
                "sunset_date": entry.sunset_date,
            }
            for entry in policy.deprecations
        ],
        "evidence": {
            "adr_count": len(_parse_adr_blocks(base_dir / "architecture_decisions.md")),
            "governance_passed": True,
            "smoke_command": "PYTHONPATH=src python3 scripts/run_architecture_governance_smoke.py",
        },
    }


def render_report(base_dir: Path, output_path: Path) -> Path:
    report = evaluate_governance(base_dir)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
