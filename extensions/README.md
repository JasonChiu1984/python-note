# extensions/

每個子資料夾對應一個教材頁（資料夾名稱 = HTML 檔名去掉 `.html`；子目錄頁面以 `__` 連接，例如 `python-313-learning-kit__python-313-complete-guide`）。

- `example.py`：只用標準函式庫、輸出固定的可實跑範例。`scripts/build_extensions.py` 會實際執行它，把 stdout 當成頁面上的「預期輸出」。
- `meta.json`：`lang`（zh／en）、`python`、`checked`（核對日期）、`intro`、`example_title`、`example_desc`、`run_note`、`case`（title、paragraphs、steps）、`updates`（text、sources）、`exercises`（q、a）。

修改後執行：

```bash
python scripts/build_extensions.py          # 重新產生各頁的「延伸學習」區塊
python scripts/build_extensions.py --check  # CI 用：檢查頁面是否與來源同步
```

重現條件：3.13、3.14 與 CPython 3.15.2 各準備獨立直譯器。設定 `EXT_PYTHON_313`、`EXT_PYTHON_314`、`EXT_PYTHON_315` 指向對應的 Python 執行檔，並在 3.13 環境安裝 `extensions/requirements-render.txt`。只執行指定頁可在命令後加資料夾名稱。完整驗收須回報 93 個範例、186 次執行；缺程式、套件或直譯器即失敗。核對模式不寫入 HTML 或離線複本，不能用更新模式代替驗收。

延伸章節中的工程案例用於教學，不是有現場量測證據的案例報告。範例輸出只代表對應的合成資料或本機測試；不表示設備、正式 API 或 Docker Engine 已驗收。依法規或標準做設計、驗收時應另核對適用版本及條件。
