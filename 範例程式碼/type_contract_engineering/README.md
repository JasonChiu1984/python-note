# Type Contract Engineering Sample

這個範例示範如何用 Python 標準庫建立可維護的型別契約工程流程。情境是工業感測資料進入 Python gateway 後，先經 payload validation，再轉成 domain dataclass，最後透過 Protocol 邊界發送 alarm 或 fail-safe 狀態。

## Architecture

```text
raw payload
  -> TypedDict contract
  -> runtime validation
  -> SensorReading dataclass
  -> alarm / fail-safe evaluation
  -> Protocol publisher
  -> contract report evidence
```

## Setup

```bash
cd 範例程式碼/type_contract_engineering
python3 -m py_compile src/type_contract_engineering/*.py scripts/run_type_contract_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_type_contract_smoke.py
```

## Configuration

| 設定 | 預設值 | 用途 |
|---|---|---|
| schema version | `1.0` | payload contract 版本 |
| temperature range | `0-50°C` | dashboard 與 alarm 預設範圍 |
| stale timeout | `30s` | 通訊逾時與 fail-safe 判定 |
| alarm threshold | `38°C` | 高溫告警門檻 |

## Verification

成功時會輸出：

```text
type contract smoke passed: schema + alarm + fail-safe + evidence
```

## Troubleshooting

| 問題 | 處理方式 |
|---|---|
| `ModuleNotFoundError` | 使用 `PYTHONPATH=src` 或直接執行 `scripts/run_type_contract_smoke.py` |
| payload validation 失敗 | 檢查 `device_id`、`point`、`value`、`unit`、`timestamp`、`status` 是否存在 |
| alarm 未觸發 | 檢查 `unit` 是否為 `C` 且 value 是否高於 threshold |
| fail-safe 未啟動 | 檢查 timestamp 與 stale timeout 的差距 |

## Best Practices

- `TypedDict` 用來描述外部 payload，不等於 runtime validation。
- `dataclass` 用來承載已驗證的 domain state。
- `Protocol` 用來隔離 publisher、repository、gateway adapter 等外部依賴。
- 工業資料流要保留 IO mapping、單位、range、timeout、alarm 與 fail-safe 說明。
