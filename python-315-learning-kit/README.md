# Python 3.15 語法與新特性學習資料包

核對與實測版本：CPython 3.15.2。整理日期：2026-11-24（Asia/Taipei）。

## 開始閱讀

直接開啟 `python-315-complete-guide.html`，可查看完整教材、章節目錄及兩張已修正的工程圖。此檔已內嵌樣式與圖表，可離線閱讀；外部連結僅用於查閱官方來源。

偏好 Obsidian 或文字版本，可開啟 `python-315-complete-guide.md`，並保留同目錄下的兩個 SVG 圖檔。

## 執行範例

解壓縮後，在本目錄執行：

```bash
python3.15 examples/core_syntax.py
python3.15 examples/new_features_315.py
python3.15 examples/concurrency_315.py
python3.15 examples/hvac_monitor_315.py --output report.json
```

Windows 可依安裝方式將 `python3.15` 換為 `py -3.15`。啟用 Python 3.15 虛擬環境後也可用 `python`。

若要比較建置與 GIL 狀態，可另外使用 free-threaded 執行檔：

```bash
python3.15t examples/concurrency_315.py
```

四支程式只使用標準函式庫與模擬資料，不需要第三方 Python 套件或網頁建置工具。執行驗證時不要加入 `-O`，以免停用範例中的 assertion。

## 檔案說明

| 檔案／目錄 | 內容 |
|---|---|
| `python-315-complete-guide.html` | 整合教材與兩張修正圖 |
| `python-315-complete-guide.md` | 可編輯的 Markdown 教材 |
| `examples/core_syntax.py` | 33 項核心語法行為驗證 |
| `examples/new_features_315.py` | 16 組 Python 3.15 新功能示範 |
| `examples/concurrency_315.py` | 新 iterator 工具、跨 interpreter 佇列、工作池與 TaskGroup |
| `examples/hvac_monitor_315.py` | 8 筆模擬測點的輸入驗證與 JSON 報告 |
| `python-315-diagrams.drawio` | 兩頁可編輯原生圖表 |
| `production-notes-cli-fixed.svg` / `.png` | 第一張圖，補齊箭頭並修正 Release／Rollback 順序 |
| `python-project-delivery-blueprint.svg` / `.png` | 第二張圖，擴大卡片並修正文字內距與下方關聯線 |
| `verification/` | 實測輸出、圖表字框量測與靜態文件檢查 |
| `SHA256SUMS.txt` | 資料包內各檔案的 SHA-256 |

一般版與 free-threaded 版皆已執行並行範例。功能驗證不等於靜態型別檢查、效能測試或現場設備測試；完整界線寫於教材與驗證紀錄。

Python 3.15 的完整官方變更：[What's New](https://docs.python.org/3.15/whatsnew/3.15.html)。
