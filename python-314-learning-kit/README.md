# Python 3.14 語法與新特性學習資料包

兩種語言可在頁首切換，兩版均可離線閱讀。直接開啟 [繁體中文 HTML](python-314-complete-guide.html) 或 [English HTML](python-314-complete-guide.en.html)，或在 Obsidian 閱讀 [Markdown 原稿](python-314-complete-guide.md)。共 16 個核心語法單元，本版特性包括 t-string、延後求值的註記、Zstandard、子直譯器及程序移植。整理日期為 2026-11-24（台北），使用 3.14.10 官方文件，實跑為 CPython 3.14.7。

## 執行範例

在解壓縮後的目錄執行下列命令。Windows 可換成 `py -3.14`，或使用虛擬環境中的 `python`。驗證時請保留 assertion。

```bash
python3.14 examples/core_syntax.py
python3.14 examples/new_features_314.py
python3.14 examples/concurrency_314.py
python3.14 examples/hvac_monitor_314.py --output report.json
```

如已安裝 free-threaded CPython，可另外使用 `python3.14t examples/concurrency_314.py` 查看建置及執行時 GIL 狀態。一般版實跑結果見 [verification.json](verification.json)。HVAC 範例只使用模擬設備資料。

自行建置的 3.14 若缺少 _zstd，Zstandard 範例會標示 SKIP，其他示範仍會執行。可用含 libzstd 的 CPython 建置重跑。

## 資料包檔案

| 檔案 | 用途 |
|---|---|
| `examples/core_syntax.py` | 33 項核心語法行為 |
| `examples/new_features_314.py` | 本版新增功能與邊界測試 |
| `examples/concurrency_314.py` | 並行、背壓、關閉 |
| `examples/hvac_monitor_314.py` | 8 個模擬測點及 JSON 報告 |
| `production-notes-cli-fixed.svg`、`python-project-delivery-blueprint.svg` | 可獨立查看的兩張工程流程圖 |
| `verification.json`、`SHA256SUMS.txt` | 測試結果及下載完整性 |

官方來源 [What's New](https://docs.python.org/3.14/whatsnew/3.14.html) · [版本支援](https://devguide.python.org/versions/)
