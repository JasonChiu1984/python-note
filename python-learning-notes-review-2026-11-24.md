# Python 學習筆記校閱報告

## 2026 年 11 月 24 日第二輪校閱

從 [教材首頁](index.html) 可進入 30 門進度課程、3.13 至 3.15 的版本教材與平行通道專題。本輪檢查專案內 36 個 HTML 檔的靜態連結、錨點、重複 ID、內嵌 JavaScript 及 HTML 事件屬性語法。內容深閱聚焦於下列有可重現差異的主題。

| 原本照著做會遇到什麼 | 已修正的教材與判斷方式 |
|---|---|
| 12 門工程課把通過 `py_compile` 解讀成依賴能正常匯入 | 拆開語法編譯、目標環境匯入與啟動驗收。部分命令中的省略號也換成實際目錄。 |
| 入門課的鎖檔可以被另一個程序覆寫，區塊出錯時也可能略過示範的清理步驟 | [入門實作](python_beginner_interactive_tutorial.html) 使用獨占建立並說明鎖檔殘留。以第二個 Python 程序驗證競爭失敗，同時驗證例外後可以重新取得鎖。context manager 的清理放入 `finally`。 |
| 畫面上有數字，容易誤以為已量測自由執行緒延遲或找到觸發 GIL 的套件 | [3.15 平行通道](python_3_15.html) 使用隨附腳本，區分取樣與執行時 GIL 狀態、佇列結束與 QSBR 回收。修正啟動檢查按鈕的引號，複製失敗時會顯示失敗提示。 |
| 讀者可能推論 gather 失敗時會取消其餘任務，或 queue.join() 回傳即代表每筆業務成功 | [非同步課](python_async_concurrency_engineering_tutorial.html) 說明第一個例外的傳遞、TaskGroup 的取消、成功取件與 task_done 的配對。Semaphore 示範改成五筆任務競用兩個名額。 |
| Pandas 空月報曾輸出 `NaN`，無窮大金額會產生 `Infinity` | [Pandas 範例](範例程式碼/pandas_etl_report/README.md) 定義無資料時缺值比例為 `null`、拒絕無窮大金額。台北 6 月 1 日 00:05 的訂單歸入 UTC 5 月，並以測試固定此月份規則。 |
| MCP 課程把歷史範例的 Content-Length 標頭教成標準 stdio 格式 | [本地知識庫課](python_local_knowledge_base_mcp_tutorial.html) 指向歷史範例，標示其自訂分幀，並說明標準 stdio 每行送出一則 UTF-8 JSON-RPC 訊息，日誌寫入 stderr。 |
| 課程有執行指令，工作目錄卻缺少範例 | 從原專案的本機 Git 版本 `39259c533d73e5f34f95fbdee0cde94f7817d377` 補回 22 個工程範例並連到各自的 README。現有 NumPy 與 Pandas 範例一併驗證。 |

### 本輪驗證

| 項目 | 結果 |
|---|---|
| CPython 3.13.15 與 3.14.7 | 各 33 項核心語法、各 3 組並行示範通過。本版新功能各 7／6 組通過。兩版各 30 個 Markdown Python 區塊可編譯，各 8 筆 HVAC 模擬結果及 JSON 檔與標準輸出一致。另測試溫度上下限、無限值與數值溢位。 |
| 24 個工程範例 | 22 個補回的專案在 3.14.7 通過 116 個 unittest。NumPy 與 Pandas 的 pytest 分別通過 3 與 5 個，共 124 個工程測試。另外用實際 CSV 驗證兩種資料產品及嚴格 JSON 輸出。 |
| 教材網頁 | 首頁課程目標與進度項目對齊。36 個 HTML、74 段內嵌腳本或事件處理程式通過靜態檢查。以模擬 DOM 測試平行通道的 16 項互動行為；複製按鈕另驗成功、拒絕與例外的回饋。 |
| Python 3.15 | 重建並核對 753 筆中英對照、兩張英文圖，以及資料包 SHA-256。3.15.2 一般與自由執行緒版本的功能結果來自先前封存紀錄。本輪本機沒有 3.15／3.15t 執行檔。 |

本輪沒有量測多核心加速比、操作實體設備，或對全部教學卡進行真實瀏覽器逐卡操作。MCP 歷史範例未在本輪與外部用戶端連線測試。

官方核對依據：[py_compile](https://docs.python.org/3.14/library/py_compile.html) · [asyncio tasks](https://docs.python.org/3.14/library/asyncio-task.html) · [asyncio queues](https://docs.python.org/3.14/library/asyncio-queue.html) · [CPython 自由執行緒](https://docs.python.org/3.15/howto/free-threading-python.html) · [取樣分析器](https://docs.python.org/3.15/library/profiling.sampling.html) · [PEP 734](https://peps.python.org/pep-0734/) · [MCP stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。

## 第一輪校閱紀錄

校閱日期為 2026 年 11 月 24 日（台北）。範圍包括教材首頁與連結、Python 3.15 完整教材及平行通道互動頁，並交叉核對版本現代化、CI/CD 與依賴環境治理三個相關課程。保留 3.15 的 16 個核心單元與工程流程，新增繁體中文 3.13 與 3.14 離線 HTML、Markdown、圖表及標準函式庫範例。

### 主要發現與修訂

| 發現 | 修訂 | 驗收依據 |
|---|---|---|
| 首頁與升級相關課程仍把 3.15 標為 beta | 更新首頁路線圖、版本現代化、CI/CD 與依賴治理。分列最低支援、目前部署、下一個升級目標與 CI 條件 | 3.15.0 已於 2026-10-09 發布。核對時 3.13、3.14、3.15 官方文件分別為 3.13.18、3.14.10、3.15.2 |
| 只有 3.15 完整版本教材，舊版缺少遷移落點 | 加入兩個版本教材，維持相同核心單元。3.13 補 `locals()`、型別預設值、`ReadOnly`、`TypeIs`、Queue 停機；3.14 補 t-string、`annotationlib`、子直譯器及 Zstandard | 兩套皆用各自版本執行，涵蓋語法、主要功能及降級策略 |
| 3.15 教材版本沿革缺少 3.13 的佇列關閉及兩項型別功能 | 補入 3.15 的中英文版本沿革表。3.13 與 3.14 的教材另提供跨版本語法/API 對照 | `queue.Queue.shutdown()` 與 `asyncio.Queue.shutdown()` 自 3.13 提供，兩者的例外來自不同模組 |
| 3.14 移植需要落到修補版本和平台 | 補 GC、程序啟動、註記內省、C 擴充檢查；並保留 3.14.0–3.14.4 的歷史 GC 說明 | 3.14.5 回復分代 GC，支援 forkserver 的 Unix 平台改預設啟動方式，macOS、Windows 維持 spawn |
| 3.15 互動示意混入未經驗證的效能與安全隔離說法 | 模擬數值改為明確標示。修正 QSBR 適用範圍、記憶體配置、`abi3t` 和 C 擴充相容性。子直譯器示例改用具有種類的停止訊息 | 佇列與部分容器操作仍有同步。子直譯器共享程序，不提供安全沙箱。跨直譯器範例實跑通過 |
| 本機目錄缺少多個首頁及教材連結的目標 | 由 `JasonChiu1984/python-note` 補回 29 個首頁目標，再補 NumPy 與 Pandas 兩個直接連結的範例專案 | 用 Git blob SHA 核對補回檔案。首頁 30 個進度課程的對應與目標檔案全部通過 |
| 3.14 壓縮示範假設所有 CPython 都有 zstd 擴充 | 3.14 範例遇到缺少 `_zstd` 時顯示 SKIP，其他功能繼續執行 | 在含 `_zstd` 與未含該擴充的兩套 3.14.7 建置分別驗證 |

官方來源 [版本列表](https://www.python.org/doc/versions/) · [3.13 更新](https://docs.python.org/3.13/whatsnew/3.13.html) · [3.14 更新](https://docs.python.org/3.14/whatsnew/3.14.html) · [3.15 更新](https://docs.python.org/3.15/whatsnew/3.15.html) · [PEP 803](https://peps.python.org/pep-0803/) · [子直譯器](https://docs.python.org/3.14/library/concurrent.interpreters.html)

### 執行結果

| 驗證 | Python 3.13 | Python 3.14 |
|---|---|---|
| macOS arm64 一般建置 | CPython 3.13.15 | CPython 3.14.7 |
| 核心語法 | 33 / 33 | 33 / 33 |
| 本版新增功能 | 7 / 7 | 6 / 6 |
| 並行與關閉 | 3 / 3，含 `as_completed` 原 Task 身分 | 3 / 3，含子直譯器佇列與工作池 |
| 各版 Markdown 的 Python 區塊 | 30 塊皆可編譯 | 30 塊皆可編譯 |
| 8 筆 HVAC 模擬讀值 | 資料品質、告警狀態、上下限及 JSON 輸出皆通過 | 同左 |
| 離線教材 | 章節與本機檔案連結、兩張內嵌 SVG 已核對 | 同左 |

檔案包含 [3.13 驗證紀錄](python-313-learning-kit/verification.json) 及 [3.14 驗證紀錄](python-314-learning-kit/verification.json)。3.15 的雙語教材重建時核對了翻譯鍵、原文、程式碼及連結結構。互動頁抽出子直譯器範例以 3.14.7 實跑，其餘修改過的頁面檢查內嵌 JavaScript 語法。3.15 核心範例沿用原先封存的實測紀錄。

### 第一輪記錄的待驗證項目

| 項目 | 驗證建議與判定依據 |
|---|---|
| 平台與依賴 | Windows、Linux 或 Raspberry Pi 必須在相同目標 OS、架構、建置與依賴下跑完整測試；比對匯入、程序啟動、UTF-8 與 wheel |
| 自由執行緒與效能 | 另以 3.13t／3.14t 執行，匯入依賴後驗 GIL。記錄相同工作量、暖機、重複次數、P95／P99、RSS 與版本 |
| 靜態型別 | 在實際使用的 mypy、Pyright 或其他工具驗 `ReadOnly` 寫入診斷、`TypeIs` 雙向縮小及泛型預設值 |
| 設備整合 | 目前使用模擬資料。部署前驗證驅動、停機、瞬斷、超時、告警去抖、過期狀態與不同資料品質 |
| 後續教材維護 | 重新發布時核對每個 minor 的官方變更、部署 patch 和驗證 patch。若更新共同核心內容，需同步 3.13、3.14、3.15；既有 3.15 雙語版需同步更新英文翻譯 |

首頁及相關課程的本機補檔與校訂已完成。第一輪校閱不涵蓋未直接連結的其他範例目錄、各課程的全部程式碼或完整瀏覽器互動矩陣。本次未發布 GitHub 變更。
