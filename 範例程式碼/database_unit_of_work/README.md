# Database Unit of Work 範例

這個範例使用 Python 標準庫 `sqlite3` 示範資料庫工程的最小可驗收邊界：

- `schema.py`：建立資料表、約束與 schema migration 記錄。
- `repository.py`：集中 SQL 與 row mapping。
- `uow.py`：用 context manager 控制 commit / rollback。
- `service.py`：示範業務邏輯只依賴 Unit of Work，不直接操作 SQL。
- `tests/`：驗證新增、unique constraint、rollback。

## 執行

```bash
PYTHONPATH=src python3 -m database_unit_of_work.demo
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

這個專案刻意不引入 SQLAlchemy 或 Alembic，方便在乾淨環境驗證；正式專案可把同樣分層遷移到 SQLAlchemy session、Alembic migration 與 PostgreSQL。
