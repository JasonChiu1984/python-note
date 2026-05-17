# knowledge_base MCP Server

這個資料夾提供本地 stdio MCP Server，讓 Codex / Claude / Cursor 可查詢 `knowledge_base/`。

## 啟動

```bash
python3 mcp_server/knowledge_base_server.py
```

## 提供工具

- `search`
  - 參數：
    - `query: string`
    - `limit?: integer`
- `read`
  - 參數：
    - `id: string`

## 設定範例

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

## 備註

- 這個 server 為零相依最小實作，方便在受限環境直接使用。
- 若後續要擴充，可再加入 `list_recent`、`read_markdown`、`upsert`、`delete` 等工具。
