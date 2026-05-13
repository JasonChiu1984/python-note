# Industrial Data Gateway 範例

此範例用 Python 標準庫示範工業資料採集 gateway 的核心邏輯，不連線真實 PLC/DDC。它聚焦在可本機驗證的部分：IO mapping、Modbus holding register 讀值、32-bit float conversion、timeout、alarm、fail-safe output，以及對 OPC UA / BACnet / MQTT 的資料契約轉換。

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
- OPC UA 範例使用 `Security=None`、port `4840`，正式現場應依 SCADA/資安政策改為加密與憑證。
- BACnet/IP 若跨 subnet，需規劃 BBMD、foreign device 與 routing。
- timeout 或 stale data 時，output decision 會回到 fail-safe 狀態。
