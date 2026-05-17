# Python 資料演進治理語法與工程知識

- ID: `2026-05-16-124900-python-data-evolution-syntax-knowledge`
- Source: `codex-summary`
- Created At: `2026-05-16T12:49:00+0800`
- Tags: `python-notes`, `syntax`, `data-evolution`, `engineering-pattern`, `knowledge-base`

## Summary

這份筆記把 `v3.3.0` 教材與範例中涉及的 Python 語法與工程知識抽出來，重點不是版本發布，而是後續可重用的實作模式：`dataclass`、typed payload、compat adapter、checkpoint、preflight、report generation、unittest 驗收與 rollback 驗證。

## Core Syntax Patterns

### 1. `@dataclass` 建模穩定資料結構

本輪範例用 `@dataclass(frozen=True)` 定義資料模型與 manifest，這種寫法適合：

- schema record
- migration manifest
- summary result
- config / contract object

典型形式：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MigrationManifest:
    from_version: int
    to_version: int
    expand_steps: tuple[str, ...]
    contract_condition: str
```

工程價值：

- 欄位意圖明確
- 建構子與型別自然固定
- 適合做 release artifact、report payload 與測試比對

### 2. 用函式集中處理版本相容讀取

本輪資料演進 sample 把相容讀取集中在 `read_record(payload)`，而不是把版本分支散落在各處：

```python
def read_record(payload: dict[str, object]) -> TelemetryRecord:
    version = int(payload.get("schema_version", 1))
    if version == 1:
        severity = str(payload.get("level", "info"))
    elif version == 2:
        severity = str(payload["severity"])
    else:
        raise DataEvolutionError(...)
```

這是典型的 `compat adapter` 模式，適合：

- API response versioning
- event payload evolution
- database record migration
- configuration schema upgrade

### 3. 以 `dict[str, object]` 作為原始 payload 邊界

範例先接受 `dict[str, object]`，再轉成強型別 model。這種寫法把責任切成兩段：

1. 原始資料先當作不可信輸入
2. 轉換成功後才進入 domain object

這比一開始就把所有欄位當成正確型別安全，特別適合：

- JSON 檔案
- API payload
- event bus message
- 本地 migration 腳本

### 4. `checkpoint` 作為可續跑任務狀態

本輪 sample 用簡單 dataclass 表示任務進度：

```python
@dataclass
class Checkpoint:
    last_processed_id: int = 0
```

這個模式的重點不是資料結構本身，而是把「續跑能力」變成顯式契約。適用於：

- backfill
- batch import
- replay
- long-running ETL

### 5. `preflight_check()` 先於 migration 執行

本輪把 drift 檢查抽成獨立函式：

```python
def preflight_check(records: list[dict[str, object]]) -> list[str]:
    ...
```

這是很典型的工程做法：

- 先列出資料不一致
- 再決定是否允許執行升版
- 不把 dirty data 問題硬塞進 migration 主流程

它對應的工程觀念是：

- validation before mutation
- fail early
- drift evidence first

## Engineering Knowledge Extracted

### Expand / Contract 不只是資料庫術語

本輪教材強調：

1. 先 `expand`
2. 保留相容讀取
3. 做 `backfill`
4. 驗證 rollback
5. 最後才考慮 `contract`

這個模式不只適用於資料庫，也適用於：

- API 欄位演進
- 事件 schema 升版
- 設定檔 schema
- 工業 telemetry point mapping

### Rollback 要驗資料，不只驗程式

這次 sample 的一個重要知識點，是把 `LegacyReader` 保留成 rollback 驗證工具：

```python
class LegacyReader:
    def read(self, payload: dict[str, object]) -> dict[str, object]:
        ...
```

關鍵觀念：

- 程式能退版，不代表資料也能退回使用
- rollback 必須驗證「舊 reader 是否仍可讀」
- 如果不能，至少要有 backup / reverse transform / restore plan

### Report 是工程產物，不是附加文件

本輪使用 `write_migration_report(...)` 把驗證結果輸出成 JSON。這對教學專案很重要，因為它說明：

- evidence 應被結構化輸出
- 成功、跳過、drift、last_processed_id、rollback_validated 都應可追溯
- release note / handoff / CI artifact 都應可引用同一份 evidence

## Testing Knowledge

### 本輪 `unittest` 驗證的知識重點

本輪 6 個測試案例反映了幾個很穩定的工程測試思路：

1. 驗 `v1 -> v2` 相容讀取
2. 驗 checkpoint 是否推進
3. 驗 resume 是否跳過已處理資料
4. 驗 drift preflight 是否抓到缺欄位
5. 驗 legacy reader 是否能讀升版後資料
6. 驗 report 是否真的被寫出

這些測試不是語法展示，而是最小可交付驗收面。

### Smoke Script 的角色

`scripts/run_data_evolution_smoke.py` 的價值在於：

- 用最短流程覆蓋主成功路徑
- 檢查 checkpoint / rollback / report 是否串得起來
- 提供 release 前快速人工驗收入口

這種 smoke script 模式也可複用在：

- config governance
- event reliability
- deployment runtime
- CI quality gate

## Reusable Python Knowledge

本輪可重用的 Python / 工程知識，可濃縮成下面幾條：

- `dataclass` 很適合定義 migration manifest、summary、config、contract。
- 原始輸入先用 `dict[str, object]` 接，再轉強型別 object，邊界比較安全。
- 相容升版邏輯應集中在 adapter / reader，不要分散在 service 內部。
- 長任務應明確保存 checkpoint，否則不算可維運。
- preflight、backfill、rollback、report 要拆開，這樣測試與交付都比較穩。
- smoke script 與 `unittest` 應共同存在，一個覆蓋快路徑，一個守住回歸。

## Evidence Sources

- `python_data_evolution_governance_tutorial.html`
- `範例程式碼/data_evolution_governance/src/data_evolution_governance/models.py`
- `範例程式碼/data_evolution_governance/src/data_evolution_governance/migration.py`
- `範例程式碼/data_evolution_governance/src/data_evolution_governance/report.py`
- `範例程式碼/data_evolution_governance/tests/test_data_evolution_governance.py`
