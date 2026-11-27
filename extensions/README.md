# extensions/

每個子資料夾對應一個教材頁（資料夾名稱 = HTML 檔名去掉 `.html`；子目錄頁面以 `__` 連接，例如 `python-313-learning-kit__python-313-complete-guide`）。

- `example.py`：只用標準函式庫、輸出固定的可實跑範例。`scripts/build_extensions.py` 會實際執行它，把 stdout 當成頁面上的「預期輸出」。
- `meta.json`：`lang`（zh／en）、`python`、`checked`（核對日期）、`intro`、`example_title`、`example_desc`、`run_note`、`case`（title、paragraphs、steps）、`updates`（text、sources）、`exercises`（q、a）。

修改後執行：

```bash
python scripts/build_extensions.py          # 重新產生各頁的「延伸學習」區塊
python scripts/build_extensions.py --check  # CI 用：檢查頁面是否與來源同步
```
