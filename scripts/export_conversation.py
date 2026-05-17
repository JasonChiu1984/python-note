from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KB_ROOT = ROOT / "knowledge_base"
ENTRIES_DIR = KB_ROOT / "entries"
INDEX_PATH = KB_ROOT / "index.json"


@dataclass
class Message:
    role: str
    content: str


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip().lower()).strip("-")
    return slug or "conversation"


def now_local() -> datetime:
    return datetime.now().astimezone()


def build_entry_id(title: str, created_at: datetime) -> str:
    return f"{created_at.strftime('%Y-%m-%d-%H%M%S')}-{slugify(title)}"


def ensure_dirs() -> None:
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_PATH.exists():
        INDEX_PATH.write_text(json.dumps({"entries": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_input(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_markdown(text: str) -> list[Message]:
    pattern = re.compile(r"^###\s+\d+\.\s+([a-zA-Z0-9_-]+)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [Message(role="document", content=text.strip())]
    messages: list[Message] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        role = match.group(1).strip().lower()
        content = text[start:end].strip()
        messages.append(Message(role=role, content=content))
    return messages


def normalize_role(value: Any) -> str:
    if not value:
        return "unknown"
    return str(value).strip().lower()


def normalize_content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("value")
                if text:
                    parts.append(str(text).strip())
            else:
                parts.append(str(item).strip())
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        text = value.get("text") or value.get("content") or value.get("value")
        if text:
            return str(text).strip()
    return str(value).strip()


def parse_json_payload(payload: Any) -> list[Message]:
    if isinstance(payload, dict):
        if isinstance(payload.get("messages"), list):
            return parse_json_payload(payload["messages"])
        if isinstance(payload.get("conversation"), list):
            return parse_json_payload(payload["conversation"])
        if "role" in payload and ("content" in payload or "text" in payload):
            return [Message(role=normalize_role(payload.get("role")), content=normalize_content(payload.get("content", payload.get("text"))))]
        return [Message(role="document", content=json.dumps(payload, ensure_ascii=False, indent=2))]
    if isinstance(payload, list):
        messages: list[Message] = []
        for item in payload:
            if isinstance(item, dict) and ("role" in item or "content" in item or "text" in item):
                role = normalize_role(item.get("role"))
                content = normalize_content(item.get("content", item.get("text")))
                if content:
                    messages.append(Message(role=role, content=content))
            else:
                messages.append(Message(role="document", content=normalize_content(item)))
        return messages
    return [Message(role="document", content=normalize_content(payload))]


def parse_input(path: Path) -> list[Message]:
    text = load_input(path)
    if path.suffix.lower() == ".md":
        return parse_markdown(text)
    if path.suffix.lower() == ".json":
        return parse_json_payload(json.loads(text))
    try:
        return parse_json_payload(json.loads(text))
    except json.JSONDecodeError:
        return parse_markdown(text)


def render_markdown(entry: dict[str, Any]) -> str:
    tags_text = ", ".join(f"`{tag}`" for tag in entry["tags"]) if entry["tags"] else "(none)"
    lines = [
        f"# {entry['title']}",
        "",
        f"- ID: `{entry['id']}`",
        f"- Source: `{entry['source']}`",
        f"- Created At: `{entry['created_at']}`",
        f"- Tags: {tags_text}",
        "",
        "## Summary",
        "",
        entry["summary"] or "(no summary)",
        "",
        "## Messages",
        "",
    ]
    for index, message in enumerate(entry["messages"], start=1):
        lines.extend(
            [
                f"### {index}. {message['role']}",
                "",
                message["content"] or "(empty)",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def update_index(entry: dict[str, Any]) -> None:
    index_payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    entries = index_payload.get("entries", [])
    entries = [item for item in entries if item.get("id") != entry["id"]]
    entries.append(
        {
            "id": entry["id"],
            "title": entry["title"],
            "source": entry["source"],
            "created_at": entry["created_at"],
            "tags": entry["tags"],
            "summary": entry["summary"],
            "json_path": f"entries/{entry['id']}.json",
            "markdown_path": f"entries/{entry['id']}.md",
        }
    )
    entries.sort(key=lambda item: item["created_at"], reverse=True)
    INDEX_PATH.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_conversation(input_path: Path, source: str, title: str | None, summary: str | None, tags: list[str]) -> dict[str, Any]:
    ensure_dirs()
    created_at = now_local()
    normalized_messages = parse_input(input_path)
    final_title = title or input_path.stem.replace("_", " ").replace("-", " ").strip().title() or "Conversation Export"
    entry_id = build_entry_id(final_title, created_at)
    entry = {
        "id": entry_id,
        "title": final_title,
        "source": source,
        "created_at": created_at.isoformat(),
        "tags": tags,
        "summary": summary or f"Imported from {input_path.name}",
        "messages": [{"role": item.role, "content": item.content} for item in normalized_messages],
    }
    json_path = ENTRIES_DIR / f"{entry_id}.json"
    markdown_path = ENTRIES_DIR / f"{entry_id}.md"
    json_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(entry), encoding="utf-8")
    update_index(entry)
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Export conversation into knowledge_base Markdown/JSON.")
    parser.add_argument("--input", required=True, type=Path, help="Path to conversation export (.json or .md).")
    parser.add_argument("--source", default="manual-import", help="Conversation source, e.g. codex/claude/cursor.")
    parser.add_argument("--title", default=None, help="Override entry title.")
    parser.add_argument("--summary", default=None, help="Override entry summary.")
    parser.add_argument("--tags", nargs="*", default=[], help="Tags for later search.")
    args = parser.parse_args()

    entry = export_conversation(
        input_path=args.input,
        source=args.source,
        title=args.title,
        summary=args.summary,
        tags=args.tags,
    )
    print(json.dumps({"id": entry["id"], "json": f"knowledge_base/entries/{entry['id']}.json", "markdown": f"knowledge_base/entries/{entry['id']}.md"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
