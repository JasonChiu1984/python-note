from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from architecture_governance.policy import GovernanceError, evaluate_governance, render_report


FIXTURE = Path(__file__).resolve().parents[1]


class ArchitectureGovernanceTests(unittest.TestCase):
    def test_report_generation(self) -> None:
        report = evaluate_governance(FIXTURE)
        self.assertTrue(report["evidence"]["governance_passed"])
        self.assertEqual(report["evidence"]["adr_count"], 2)

    def test_render_report_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            render_report(FIXTURE, output)
            self.assertTrue(output.exists())
            self.assertIn('"governance_passed": true', output.read_text(encoding="utf-8"))

    def test_missing_owner_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "architecture_decisions.md").write_text(
                "## ADR-001\n- context: x\n- decision: y\n- tradeoff: z\n- replacement_trigger: t\n",
                encoding="utf-8",
            )
            (base / "module_ownership.json").write_text('{"domain":"team-domain"}\n', encoding="utf-8")
            (base / "import_rules.json").write_text(
                '{"domain":[],"application":["domain"],"adapters":["application","domain"],"interfaces":["application","domain"],"legacy_gateway":["application"]}\n',
                encoding="utf-8",
            )
            with self.assertRaises(GovernanceError):
                evaluate_governance(base)

    def test_disallowed_import_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "architecture_decisions.md").write_text(
                "## ADR-001\n- context: x\n- decision: y\n- tradeoff: z\n- replacement_trigger: t\n",
                encoding="utf-8",
            )
            (base / "module_ownership.json").write_text(
                '{"domain":"team-domain","application":"team-core","adapters":"team-integrations","interfaces":"team-platform","legacy_gateway":"team-core"}\n',
                encoding="utf-8",
            )
            (base / "import_rules.json").write_text(
                '{"domain":[],"application":["domain"],"adapters":["domain"],"interfaces":["application","domain"],"legacy_gateway":["application"]}\n',
                encoding="utf-8",
            )
            with self.assertRaises(GovernanceError):
                evaluate_governance(base)

    def test_missing_adr_fields_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "architecture_decisions.md").write_text(
                "## ADR-001\n- context: x\n- decision: y\n",
                encoding="utf-8",
            )
            (base / "module_ownership.json").write_text(
                '{"domain":"team-domain","application":"team-core","adapters":"team-integrations","interfaces":"team-platform","legacy_gateway":"team-core"}\n',
                encoding="utf-8",
            )
            (base / "import_rules.json").write_text(
                '{"domain":[],"application":["domain"],"adapters":["application","domain"],"interfaces":["application","domain"],"legacy_gateway":["application"]}\n',
                encoding="utf-8",
            )
            with self.assertRaises(GovernanceError):
                evaluate_governance(base)
