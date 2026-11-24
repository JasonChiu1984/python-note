# 工業通訊實作範例

八種範例共用 AHU01.SAT 測點。完整的位址、流程、比較表與實機步驟見 [工業協定教材](../../python_industrial_protocol_comparison_tutorial.html#protocol-lab)。

## 離線運行

Python 3.11 以上，於此目錄執行，僅使用標準函式庫。

```bash
python protocol_lab.py all
python protocol_lab.py modbus
python protocol_lab.py bacnet
python protocol_lab.py opcua
python protocol_lab.py mqtt
python protocol_lab.py zigbee
python protocol_lab.py profinet
python protocol_lab.py profibus
python protocol_lab.py cc-link
```

每種用例預期 22.0 °C。OPC UA 故意產生 uncertain，其餘固定用例預期 good。離線模式以 SDK 解碼結果或 PLC 快照為資料，實際發送與接收由下一節的實機模式及對應主站負責。

## 決定實機路徑

| 路徑 | 前置條件 | 執行方式 |
|---|---|---|
| Modbus TCP／RTU | 安裝 `pymodbus`（支援 `device_id` 的版本），RTU 另安裝 `pyserial` | `python read_live.py modbus --help` |
| BACnet/IP | 安裝 asyncio 版 `BAC0`，準備可綁定的樓控測試網卡與點表 | `python read_live.py bacnet --help` |
| OPC UA | 安裝 `asyncua`；準備 UA Endpoint、Namespace URI、NodeId 與雙端信任憑證 | `python read_live.py opcua --help` |
| MQTT／Zigbee | 安裝 `paho-mqtt>=2,<3`；準備 TLS broker 與 topic。Zigbee 另需協調器與 Zigbee2MQTT | `python read_live.py mqtt --help`、`python read_live.py zigbee --help` |
| PROFINET IO／PROFIBUS DP／CC-Link Classic | 支援對應協定的 PLC／主站或工業閘道。在主站配置循環 I/O，從同一個控制週期取得值與品質 | `python protocol_lab.py profinet --snapshot pn.json` 等 |

將教材內的文件用位址與憑證換成已授權的測試環境。MQTT 讀取腳本使用 TLS 並訂閱單一 topic；範例預期 broker 允許測試用唯讀連線。三種現場匯流排的 JSON 由 PLC／主站側程式輸出，例如透過已有的 OPC UA 讀值或閘道路徑匯出，快照格式由教材範例固定。實機程式須依設備或模組手冊核對機型、I/O 布局及診斷位元後再接入。

### 驗收

- 用單一可信測點核對數值、單位、來源位址與品質，接著加入負數與上下限。
- 記錄通訊逾時、壞品質與程式解碼錯誤；讀值失效時把狀態交給上游告警或顯示層。
- 動態測試請記錄來源時間戳、接收時間、遺漏與恢復時間。硬體掃描週期及網段容量需在現場量測。
