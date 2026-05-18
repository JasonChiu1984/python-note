# knowledge_base

這個資料夾用來存放「對話匯出後的知識庫條目」。設計目標：

1. 對話原始內容可同時落成 `Markdown` 與 `JSON`
2. 可被 MCP Server 以 `search` / `read` 工具查詢
3. 可供 Codex / Claude / Cursor 指向同一份本地知識來源

## 目錄結構

```text
knowledge_base/
├─ README.md
├─ index.json
└─ entries/
   ├─ 2026-05-14-154500-example-chat.json
   └─ 2026-05-14-154500-example-chat.md
```

## JSON 格式

每個條目都會輸出一份標準化 JSON：

```json
{
  "id": "2026-05-14-154500-example-chat",
  "title": "Example Chat",
  "source": "codex-export",
  "created_at": "2026-05-14T15:45:00+08:00",
  "tags": ["codex", "architecture"],
  "summary": "簡短摘要",
  "messages": [
    {
      "role": "user",
      "content": "請分析目前專案架構"
    },
    {
      "role": "assistant",
      "content": "以下是可改善處..."
    }
  ]
}
```

## Markdown 格式

Markdown 以可閱讀、可全文檢索為主，格式固定：

```md
# Example Chat

- ID: `2026-05-14-154500-example-chat`
- Source: `codex-export`
- Created At: `2026-05-14T15:45:00+08:00`
- Tags: `codex`, `architecture`

## Summary

簡短摘要

## Messages

### 1. user

請分析目前專案架構

### 2. assistant

以下是可改善處...
```

## 匯入方式

使用腳本：

```bash
python3 scripts/export_conversation.py \
  --input /path/to/conversation.json \
  --source codex \
  --title "專案架構審視"
```

如果輸入本身是 Markdown，也可直接匯入：

```bash
python3 scripts/export_conversation.py \
  --input /path/to/conversation.md \
  --source cursor
```

## MCP Server

本專案提供零相依的 stdio MCP Server：

```bash
python3 mcp_server/knowledge_base_server.py
```

目前提供兩個工具：

- `search`
  - 依關鍵字搜尋 `title`、`summary`、`tags`、`messages`
- `read`
  - 依 `id` 讀取單一條目全文

## Client 設定方向

Codex / Claude / Cursor 只要支援本地 MCP stdio server，都可用類似設定：

```json
{
  "mcpServers": {
    "python-notes-kb": {
      "command": "python3",
      "args": ["mcp_server/knowledge_base_server.py"],
      "cwd": "/Users/jasonchiu/Documents/CodexData/Python學習筆記"
    }
  }
}
```

## Best Practices

- 先保留標準化 JSON，再從 JSON 生成 Markdown，避免格式漂移。
- `title`、`summary`、`tags` 應盡量在匯出時補齊，讓搜尋品質更穩定。
- 需要跨工具查詢時，優先用 `id` 作為穩定鍵，而不是檔名顯示文字。
- 範例匯出與 smoke 驗證資料應視為暫存或教學素材，不應長期保留在正式 `index.json` 發布內容中。
