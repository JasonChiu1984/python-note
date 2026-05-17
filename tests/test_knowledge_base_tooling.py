from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class KnowledgeBaseToolingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.export_mod = load_module("export_conversation", ROOT / "scripts" / "export_conversation.py")
        self.server_mod = load_module("knowledge_base_server", ROOT / "mcp_server" / "knowledge_base_server.py")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.kb_root = self.root / "knowledge_base"
        self.entries_dir = self.kb_root / "entries"
        self.index_path = self.kb_root / "index.json"

        self.export_mod.KB_ROOT = self.kb_root
        self.export_mod.ENTRIES_DIR = self.entries_dir
        self.export_mod.INDEX_PATH = self.index_path
        self.export_mod.now_local = lambda: datetime(2026, 5, 17, 17, 25, 35, tzinfo=timezone.utc)

        self.server_mod.KB_ROOT = self.kb_root
        self.server_mod.INDEX_PATH = self.index_path

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_export_updates_index_and_markdown(self) -> None:
        input_path = self.root / "conversation.json"
        input_path.write_text(
            json.dumps({"messages": [{"role": "user", "content": "請建立本地知識庫"}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        entry = self.export_mod.export_conversation(
            input_path=input_path,
            source="test",
            title="Knowledge Base Contract",
            summary="test summary",
            tags=["codex", "mcp"],
        )

        json_path = self.entries_dir / f"{entry['id']}.json"
        markdown_path = self.entries_dir / f"{entry['id']}.md"
        self.assertTrue(json_path.exists())
        self.assertTrue(markdown_path.exists())

        index_payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.assertEqual(index_payload["entries"][0]["id"], entry["id"])
        markdown_text = markdown_path.read_text(encoding="utf-8")
        self.assertIn("# Knowledge Base Contract", markdown_text)
        self.assertIn("## Messages", markdown_text)

    def test_search_and_read_return_exported_entry(self) -> None:
        input_path = self.root / "conversation.md"
        input_path.write_text(
            "# Demo\n\n### 1. user\n\n請查詢 integration note\n\n### 2. assistant\n\n已新增 search 工具\n",
            encoding="utf-8",
        )

        entry = self.export_mod.export_conversation(
            input_path=input_path,
            source="test",
            title="Integration Search Note",
            summary="integration note summary",
            tags=["integration", "search"],
        )

        results = self.server_mod.search_entries("integration", limit=5)
        self.assertEqual(results[0]["id"], entry["id"])

        loaded = self.server_mod.load_entry(entry["id"])
        self.assertEqual(loaded["summary"], "integration note summary")
        self.assertEqual(loaded["messages"][0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
