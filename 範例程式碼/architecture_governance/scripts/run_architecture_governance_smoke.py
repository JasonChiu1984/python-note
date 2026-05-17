from __future__ import annotations

from pathlib import Path

from architecture_governance.policy import render_report


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    report_path = base_dir / "architecture_governance_report.json"
    render_report(base_dir, report_path)
    print("architecture governance smoke passed: adr + ownership + import rules + deprecation + report")
    print(report_path)


if __name__ == "__main__":
    main()
