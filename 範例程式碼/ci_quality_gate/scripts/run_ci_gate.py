from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ci_quality_gate import build_release_evidence, evaluate_gate  # noqa: E402


def main() -> int:
    report = evaluate_gate(ROOT, version="0.1.0", commit="local")
    evidence = build_release_evidence(report)
    evidence_path = ROOT / "ci_gate_evidence.json"
    evidence_path.write_text(evidence + "\n", encoding="utf-8")
    if report.passed:
        print("ci quality gate passed: compile + tests + coverage + matrix + workflow")
        return 0
    print(evidence)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
