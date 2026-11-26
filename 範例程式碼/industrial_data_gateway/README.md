# Industrial Data Gateway 範例

此範例用 Python 標準庫示範工業資料採集 gateway 的核心邏輯，不連線真實 PLC/DDC。它聚焦在可本機驗證的部分：IO mapping、Modbus holding register 讀值、32-bit float conversion、逾時、告警、模擬的安全狀態欄位，以及對 OPC UA／BACnet／MQTT 的資料格式轉換。它不開網路連線、不寫入設備，也不提供實體安全連鎖或持久佇列。

## 架構

```text
MockModbusDevice
  -> GatewayPoint IO map
  -> IndustrialGateway poll cycle
  -> AlarmEvent / PointReading
  -> OPC UA node payload
  -> BACnet object payload
  -> MQTT telemetry payload
```

## 範例點位

| 點位 | Modbus | 資料型別 | Word Order | OPC UA NodeId | BACnet Object |
|---|---|---|---|---|---|
| `boiler_supply_temp` | 40001 / FC03 | float32 | big | `ns=2;s=Boiler.SupplyTemperature` | `analog-input,1` |
| `pump_run_feedback` | 40011 / FC03 | uint16 | n/a | `ns=2;s=Pump.RunFeedback` | `binary-input,2` |

## 執行

```bash
python3 -m py_compile src/industrial_data_gateway/*.py scripts/run_gateway_smoke.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/run_gateway_smoke.py
```

## 現場注意

- 真實 Modbus TCP 預設 port 常見為 `502`，此範例不開 socket。
- OPC UA 範例的 `Security=None` 與 `4840` 只是輸出欄位，沒有 OPC UA 端點在監聽。正式部署以設備實際端點、受信憑證、適用的簽章與加密模式及唯讀授權為準。
- BACnet/IP 單播、跨 IP 子網廣播及跨 BACnet 網路路由分開評估；有跨子網廣播需求時才規劃 BBMD／Foreign Device。
- 逾時或資料陳舊時，報告反映程式的模擬決策；沒有輸出動作。正式安全控制由已驗證的 PLC 或安全系統負責。

- `last_scan_duration_seconds` 是整輪耗時；FC03 不提供來源時間，所以 `age_seconds` 未知，不以整輪耗時推定資料陳舊。BACnet 預覽的 `quality` 是報表欄位，不是線上物件屬性。
