# Python 3.13 語法與新特性學習資料包

兩種語言可在頁首切換，兩版均可離線閱讀。直接開啟 [繁體中文 HTML](python-313-complete-guide.html) 或 [English HTML](python-313-complete-guide.en.html)，或在 Obsidian 閱讀 [Markdown 原稿](python-313-complete-guide.md)。共 16 個核心語法單元，本版特性包括 locals() 快照、型別參數預設值、ReadOnly、TypeIs 與 Queue 關閉。整理日期為 2026-11-24（台北），使用 3.13.18 官方文件，實跑為 CPython 3.13.15。

## 執行範例

在解壓縮後的目錄執行下列命令。Windows 可換成 `py -3.13`，或使用虛擬環境中的 `python`。驗證時請保留 assertion。

```bash
python3.13 examples/core_syntax.py
python3.13 examples/new_features_313.py
python3.13 examples/concurrency_313.py
python3.13 examples/hvac_monitor_313.py --output report.json
```

如已安裝 free-threaded CPython，可另外使用 `python3.13t examples/concurrency_313.py` 查看建置及執行時 GIL 狀態。一般版實跑結果見 [verification.json](verification.json)。HVAC 範例只使用模擬設備資料。

SQLite 示範需要具 sqlite3 支援的 CPython 建置。

## 資料包檔案

| 檔案 | 用途 |
|---|---|
| `examples/core_syntax.py` | 33 項核心語法行為 |
| `examples/new_features_313.py` | 本版新增功能與邊界測試 |
| `examples/concurrency_313.py` | 並行、背壓、關閉 |
| `examples/hvac_monitor_313.py` | 8 個模擬測點及 JSON 報告 |
| `production-notes-cli-fixed.svg`、`python-project-delivery-blueprint.svg` | 可獨立查看的兩張工程流程圖 |
| `verification.json`、`SHA256SUMS.txt` | 測試結果及下載完整性 |

官方來源 [What's New](https://docs.python.org/3.13/whatsnew/3.13.html) · [版本支援](https://devguide.python.org/versions/)
