# Python 3.15 語法與新特性學習資料包

核對與實測版本：CPython 3.15.2。整理日期：2026-11-24（Asia/Taipei）。

## 開始閱讀

直接開啟 `python-315-complete-guide.html`，可查看完整教材、章節目錄及兩張已修正的工程圖。此檔已內嵌中英文內容、樣式、圖表與語言切換程式，可離線閱讀；外部連結僅用於查閱官方來源。

偏好 Obsidian 或繁體中文原稿，可開啟 `python-315-complete-guide.md`，並保留同目錄下的兩個中文 SVG 圖檔。

## 中文／English 切換

- 使用頁首固定顯示的「中文」與「English」按鈕，切換正文、標題、表格、目錄、圖說與圖表標籤。
- 預設為繁體中文；瀏覽器允許儲存時，會記住上次選擇。儲存不可用時，當次閱讀仍可正常切換。
- 連結可加上 `?lang=en` 或 `?lang=zh-Hant` 指定語言，並保留章節錨點，例如 `python-315-complete-guide.html?lang=en#section-24`。
- 切換時保留目前閱讀區塊；上一頁／下一頁會同步恢復連結指定的語言。
- 程式碼、API 名稱及範例資料維持一致。列印使用目前選擇的語言。

兩種語言的內容與圖表均內嵌於 HTML，可離線切換。

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
| `python-315-complete-guide.html` | 可切換繁體中文／英文的完整教材與圖表 |
| `python-315-complete-guide.md` | 可編輯的繁體中文 Markdown 原稿 |
| `examples/core_syntax.py` | 33 項核心語法行為驗證 |
| `examples/new_features_315.py` | 16 組 Python 3.15 新功能示範 |
| `examples/concurrency_315.py` | 新 iterator 工具、跨 interpreter 佇列、工作池與 TaskGroup |
| `examples/hvac_monitor_315.py` | 8 筆模擬測點的輸入驗證與 JSON 報告 |
| `python-315-diagrams.drawio` | 兩頁可編輯原生圖表 |
| `production-notes-cli-fixed.svg` / `.png` | 第一張圖，補齊箭頭並修正 Release／Rollback 順序 |
| `python-project-delivery-blueprint.svg` / `.png` | 第二張圖，擴大卡片並修正文字內距與下方關聯線 |
| `production-notes-cli-fixed.en.svg` / `python-project-delivery-blueprint.en.svg` | 英文圖表；網頁英文模式使用的向量版本 |
| `translations/en.json` | 英文翻譯與對應中文原文，供校對與維護 |
| `assets/language-switch.js` / `.css` | 語言切換與控制列原始碼，發布時內嵌於 HTML |
| `verification/` | 實測輸出、圖表字框量測與靜態文件檢查 |
| `SHA256SUMS.txt` | 資料包內各檔案的 SHA-256 |

一般版與 free-threaded 版皆已執行並行範例。功能驗證不等於靜態型別檢查、效能測試或現場設備測試；完整界線寫於教材與驗證紀錄。

雙語網頁完成 13 項 DOM 行為檢查，涵蓋完整翻譯、切換還原、偏好記憶、URL 優先順序、歷史導覽、離線使用、儲存受限及閱讀位置邏輯。英文圖表已實際渲染並量測文字邊界。本地執行環境無法啟動 Chromium，因此這份 DOM 報告不代表瀏覽器版面或端到端實測；詳見 `verification/language-switch-result.json`。

## 維護雙語網頁

修改 `translations/en.json` 或 `assets/language-switch.*` 後，在 GitHub 儲存庫根目錄執行：

```bash
python scripts/build_python315_bilingual.py
```

這個標準函式庫工具會核對中文原文、翻譯鍵、HTML 結構、連結與程式碼，再將英文內容、圖表及切換程式嵌回單一 HTML。中文原文改動時，也要同步校對翻譯檔中對應的 `source` 與 `translation`。發布資料包前應重新產生 SHA-256 清單與 ZIP。

Python 3.15 的完整官方變更：[What's New](https://docs.python.org/3.15/whatsnew/3.15.html)。
