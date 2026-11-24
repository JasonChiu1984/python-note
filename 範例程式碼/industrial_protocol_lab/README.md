# 八種工業通訊實作

在此目錄使用 Python 3.11 以上。先執行八種離線範例，再按協定啟動測試端點或接入實機。教材的共同測試值是 22.0 °C。Zigbee 範例的無線裝置在現場應映射為室溫或獨立測點，其餘例子使用 AHU01.SAT 送風溫度。

[八協定優缺點與使用場景](../../python_industrial_protocol_comparison_tutorial.html#protocol-selection) · [速度快慢比較](../../python_industrial_protocol_comparison_tutorial.html#protocol-speed-compare) · [通訊速度、安全性與驗收](../../python_industrial_protocol_comparison_tutorial.html#protocol-speed-security)

## 1. 不用設備的離線練習

```bash
python3 protocol_lab.py all
```

輸出八行 JSON，每種用例預期 22.0 °C。OPC UA 故意輸出 `uncertain`，其餘為 `good`。可將 `all` 替換成 `modbus`、`bacnet`、`opcua`、`mqtt`、`zigbee`、`profinet`、`profibus` 或 `cc-link`。

```bash
python3 -m venv .venv
source .venv/bin/activate
# 依所選練習安裝對應套件
python -m pip install 'pymodbus==3.11.1' pyserial
python -m pip install BAC0
python -m pip install asyncua
python -m pip install 'paho-mqtt==2.1.0'
```

兩個終端都在此目錄啟用同一個虛擬環境。以下終端 A 維持服務，終端 B 執行讀取。網路範例都只採集資料。實機請換成自己的設備位址、點表與憑證。

## 2. Modbus TCP 與 RTU

```bash
# 終端 A
python lab_endpoints.py modbus
# 終端 B
python read_live.py modbus 127.0.0.1 --port 15020 --unit 7 --offset 0
```

本機伺服器提供 FC03、Unit 7、起點 0、數量 2。請求 PDU 為 `03 00 00 00 02`，回應 PDU 為 `03 04 41 B0 00 00`。TCP 的 MBAP header 帶交易編號、Protocol ID、長度與 Unit ID。改 offset 為 1，可驗證例外回應。省略 `--port` 會走典型 TCP 502。

RTU 換成串口及設備實際設定。以 TCP-to-RTU 閘道（如 EKI-1222）連接時，用 TCP 模式並以 Unit ID 選下游站。串口模式範例：

```bash
python read_live.py modbus /dev/ttyUSB0 --serial --unit 7 --baudrate 9600 --parity E --stopbits 1
```

核對設備手冊定義的 parity、終端與偏壓，先試一台。將讀值分成通訊成功、協定例外、數值有效三個判斷。字序錯誤可能解成極小非零值，因此還要比對設備面板和工程範圍。教材的已知 float 建議加測 `22.1`，此時兩個 word 都有資訊。PyModbus 的 `device_id` 與舊版安裝範例的 `slave` 參數差異以套件版本為準。

## 3. BACnet/IP

```bash
# 終端 A
python lab_endpoints.py bacnet
# 終端 B
python read_live.py bacnet 127.0.0.1:47809 --bind 127.0.0.1/32 --instance 1
```

測試端是 Device 420101、Analog Input 1，客戶端預設 Device 420100。這個測試使用不同 UDP 埠並明確指定目的位址。如果平台無法在 loopback 建立 BACnet/IP socket，將兩端的 bind 換成同一台主機的測試網卡 IPv4／prefix，並將目標換成該 IP 加 `:47809`。到 EBO 或 DDC 上線前，從物件表核對 `presentValue`、`units`、`statusFlags` 與可用服務。

```bash
# 跨網加入已配置的測試 BBMD
python read_live.py bacnet 192.0.2.41 --bind 192.0.2.10/24 --instance 1 \
  --bbmd 192.0.2.2:47808 --bbmd-ttl 300
```

確認網路確實配置 Foreign Device 註冊，驗證 FDT、TTL 續期及廣播範圍。固定可達的 BACnet/IP 位址可先用單播讀值，用 `Who-Is/I-Am` 驗證 discovery。需要 COV 的長連線可對已建立的 BAC0 裝置與點物件呼叫 `await device['SAT'].subscribe_cov(lifetime=90)`，再驗證增量門檻、初始值、有效期和重建。如果連線仍在但溫度不變，應透過生命週期與受限回讀判斷新鮮度。參考 [BAC0 COV](https://bac0.readthedocs.io/en/latest/cov.html)。

## 4. OPC UA

```bash
# 終端 A，服務輪播 22.0、22.5、−5.0 和 BadNoData
python lab_endpoints.py opcua
# 終端 B，先讀一次，再收四次通知
python read_live.py opcua opc.tcp://127.0.0.1:4840/lab/ urn:example:plant AHU01.SAT
python read_live.py opcua opc.tcp://127.0.0.1:4840/lab/ urn:example:plant AHU01.SAT --watch 4 --timeout 15
```

伺服器的 NoSecurity 端點只綁 loopback。第一個通知通常是目前值，因此四筆通知的順序取決於連線時間。取消訂閱時清理 MonitoredItem；總逾時會中止讀取。正式接入包含 SecurityPolicy、雙端信任與帳號授權，依 Server 廠牌支援調整。腳本示範 Basic256Sha256，讀取實機範例：

```bash
python read_live.py opcua opc.tcp://192.0.2.42:4840 urn:example:plant AHU01.SAT \
  --certificate client.der --private-key client-key.pem --server-certificate server.der
```

以 UAExpert 核對 Namespace URI、NodeId 型別、DataType 與 StatusCode。範例使用 String NodeId、500 ms publishing interval 並保留來源時間戳。實機若使用 Numeric NodeId，要依設備點表調整 `ua.NodeId` 的參數型別。測試中斷後重連、重新求 namespace index、重建訂閱以及斷線資料缺口。

## 5. MQTT 5 與 Zigbee2MQTT

先安裝 Mosquitto broker 與命令列客戶端。建立只供本機練習的 `mosquitto-lab.conf`：

```conf
listener 1883 127.0.0.1
allow_anonymous true
```

```bash
# 終端 A
mosquitto -c mosquitto-lab.conf -v
# 終端 B 先訂閱
python read_live.py mqtt 127.0.0.1 site/lab/ahu01/telemetry --loopback-plaintext --wait 60
# 終端 C 等 B 建立訂閱後發布
mosquitto_pub -h 127.0.0.1 -V mqttv5 -q 1 -t site/lab/ahu01/telemetry \
  -m '{"schema":1,"point":"AHU01.SAT","value":22.0,"unit":"degC","quality":"good"}'
```

以 `retain`、訊息時間、接收時間和是否覆寫舊值分別驗收。可先用 `mosquitto_pub -r` 發布快照後才啟動讀取，確認快照沒有觸發本腳本，再送一個新上報。正式 JSON 建議再帶 `source_ts` 和 `event_id`，由應用層檢查過期、實作冪等與持久去重。Broker Ack 表示 broker 收到，業務處理成功另由應用回報。

Zigbee 的**橋接格式**可以沿用本機 broker 先驗證：

```bash
# 終端 B
python read_live.py zigbee 127.0.0.1 zigbee2mqtt/ahu01-room --loopback-plaintext --wait 60
# 終端 C，先送只有 battery 的封包，再送溫度
mosquitto_pub -h 127.0.0.1 -t zigbee2mqtt/ahu01-room -m '{"battery":95}'
mosquitto_pub -h 127.0.0.1 -t zigbee2mqtt/ahu01-room -m '{"temperature":22.0,"battery":95,"linkquality":128}'
```

驗證真正射頻鏈路時，接上 Zigbee2MQTT 支援的協調器，將 MQTT server 與 serial port 設定成實際值，在前端短暫開放加入。配對成功後以裝置頁的 IEEE 位址與 Exposes 核對 `temperature`，命名 `ahu01-room`，關閉加入，等待感測器上報。若知道裝置預設上報時間，可按同一週期調整 `--wait`。將設備 availability 與溫度最近上報時間分開保存。若橋接器在其他屬性更新時附帶快取溫度，整包狀態的接收時間只能證明 MQTT 訊息到達，溫度的實際時間須由裝置報告或額外欄位確認。

接正式或異機 broker 使用 TLS、CA 與 topic ACL。以下 client 示範由伺服器驗證與 ACL 保護的唯讀測試 listener，依現場需求在自己的 client 設定補上帳號或 mTLS。

```bash
python read_live.py mqtt broker.lab.example site/lab/ahu01/telemetry --ca lab-ca.pem
python read_live.py zigbee broker.lab.example zigbee2mqtt/ahu01-room --ca lab-ca.pem --wait 120
```

## 6. PROFINET、PROFIBUS DP、CC-Link 讀取 PLC 快照

工程設定完成前，可用匯流排各自的 JSON 格式驗收：

```bash
printf '%s\n' '{"device":"ahu01-io","slot":2,"subslot":1,"valid":true,"bytes":"00 DC"}' > pn.json
printf '%s\n' '{"station":5,"input_offset":0,"data_exchange":true,"bytes":"FF CE"}' > dp.json
printf '%s\n' '{"station":1,"rwr0":220,"link_ok":false}' > cc.json
python protocol_lab.py profinet --snapshot pn.json   # 22.0, good
python protocol_lab.py profibus --snapshot dp.json   # −5.0, good
python protocol_lab.py cc-link --snapshot cc.json    # null, bad
```

實機由主站從同一掃描取得診斷與值，再發布單一欄位。範例採三個 byte，格式為 `[有效旗標 0/1, 高位元組, 低位元組]`。例如 `01 00 DC` 是 22.0 °C、`01 FF CE` 是 −5.0 °C、`00 00 DC` 是已失效值。以下 TIA Portal SCL 片段適用於 PROFINET 子模組或 PROFIBUS DP 模組。宣告 `ModuleHwId: HW_IO`、`RawInput: ARRAY[0..1] OF BYTE`、`Rc: INT`、`StationDataOK: BOOL` 和 `Snapshot: ARRAY[0..2] OF BYTE`。硬體 ID 用 TIA 的系統常數，站有效訊號以主站／模組診斷為來源。範例 I/O 長度恰為兩個 bytes，實際模組較長時，`RawInput` 必須配合整個模組資料長度。

```text
#Rc := DPRD_DAT(LADDR := #ModuleHwId, RECORD => #RawInput);
#Snapshot[0] := 0;
#Snapshot[1] := 0;
#Snapshot[2] := 0;
IF (#Rc = 0) AND #StationDataOK THEN
    #Snapshot[0] := 1;
    #Snapshot[1] := #RawInput[0];
    #Snapshot[2] := #RawInput[1];
END_IF;
```

在 S7-1200 需依 [Siemens 指令手冊](https://docs.tia.siemens.cloud/r/simatic_s7_1200_manual_collection_itit_20/extended-instructions/distributed-i/o-profinet-profibus-or-as-i/others/dprd_dat-and-dpwr_dat-read/write-consistent-data) 設定一致性讀取及 process image。若專案已透過 process image 提供所需一致性，直接使用相應程序映像與診斷。將 OPC UA 變數映射到閘道一次送出的 ByteString／Byte 陣列，或請 PLC 原生 UA Server／閘道證明可一致地讀出整筆欄位，避免獨立讀三個 scalar 造成跨掃描混讀。

| 協定 | 實機工程設定 | 取值與驗收 |
|---|---|---|
| PROFINET IO | TIA Portal 匯入設備 GSDML，掛到 IO Controller 的 PN 網路，依實體配置 Slot/Subslot，使用同一 L2 測試網段以 DCP 指派設備名稱，例如 `ahu01-io`。 | 線上核對模組組態、I/O address、HW ID、更新時間及診斷有效。測線纜中斷、設備名稱未配置、子模組不符及重建 AR 後的復歸。 |
| PROFIBUS DP | 使用 DP Master 介面與 DP 設備的 GSD，配置唯一站號 5、相符模組、輸入長度及總線速率。RS-485 段兩端終端須依設備規格啟用並供電。 | 在 master 診斷先確認進入 Data_Exchange，再核對站內 offset 與 PLC 絕對位址。站離線或診斷指示通道無效時改送旗標 0，保留站診斷原因。 |
| CC-Link Classic | 在 GX Works／模組參數內配置 CC-Link Master、站 1、站種、占用站數、速率、Link Refresh。將站 1 RWr 的第一個 word 映射至 CPU 的一個資料字，例如 D100，僅供教材示意。 | 檢查主站模組的資料鏈路與該站錯誤位元。將 D100 視為原始 WORD，`high=(word >> 8) & 0xFF`，`low=word & 0xFF`，與 link status 組成快照。測遠端站離線時主站保留舊值的行為，確認旗標仍轉 0。 |

若設備使用 **CC-Link IE Field Basic**，在具備該功能的 CPU 或乙太網路模組啟用對應主站，設定測試站 IP、占用站數、循環逾時及 CPU 的 RX／RWr 刷新位址。使用相同的三個 byte 匯出方式。逐站以正常值、拔除網線、重新加入三種狀態驗證品質。CC-Link IE Field 和 CC-Link IE TSN 分別使用其對應主站和工程模式。選型時先核對型號相容表及 [CLPA 各版本規格](https://www.cc-link.org/en/networktechnology/index.html)。

使用前述 OPC UA 測試端點就能先驗證三個 PLC 快照 client。這三個節點是教學用的合成值，硬體接入時以現場閘道 NodeId 代換。

```bash
python read_live.py opcua opc.tcp://127.0.0.1:4840/lab/ urn:example:plant AHU01.PROFINET.Snapshot --fieldbus profinet
python read_live.py opcua opc.tcp://127.0.0.1:4840/lab/ urn:example:plant AHU01.PROFIBUS.Snapshot --fieldbus profibus
python read_live.py opcua opc.tcp://127.0.0.1:4840/lab/ urn:example:plant AHU01.CCLink.Snapshot --fieldbus cc-link --watch 4 --timeout 15
```

**現場驗收**依序比對工程單位與符號、切斷來源、記錄傳到上位系統的壞品質延遲、恢復連線，再確認新值恢復時間。將測點品質、資料新鮮度與主站／模組診斷分開記錄。PLC/DDC 管理控制循環及設備失聯策略。
