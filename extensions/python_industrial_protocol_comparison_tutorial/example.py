"""同一個「送風溫度 22.5 °C」在 Modbus、BACnet、MQTT 中的資料表示方式對照（標準函式庫）。"""
import json
import struct

value = 22.5

# Modbus：兩種常見做法——INT16 乘以 10，或 FLOAT32 佔兩個暫存器（字組順序依設備而定）
int16 = struct.pack(">h", round(value * 10))
f32 = struct.pack(">f", value)
print(f"Modbus INT16×10：暫存器 0x{int16.hex()}（{struct.unpack('>h', int16)[0]}，讀取端需知道倍率 0.1）")
hi, lo = f32[:2], f32[2:]
print(f"Modbus FLOAT32：高字組在前 {hi.hex()} {lo.hex()}；若設備低字組在前，讀成 {struct.unpack('>f', lo + hi)[0]:.3e}")

# BACnet：Analog Input 的 Present_Value 是 REAL，物件本身帶單位與狀態旗標
bacnet_tag = bytes([0x44]) + struct.pack(">f", value)          # 應用標籤 4（REAL），長度 4
print(f"BACnet REAL 編碼：{bacnet_tag.hex(' ')}；單位由 Units 屬性提供（degrees-celsius = 62）")

# MQTT：payload 格式由專案自訂，常見 JSON
payload = json.dumps({"point": "AHU1_SAT", "value": value, "unit": "degC", "ts": "2026-11-28T02:00:00Z", "q": "good"})
print(f"MQTT payload（{len(payload)} bytes）：{payload}")

print("\n比較：")
rows = [("Modbus", "只有數值，單位與倍率要看點位表", "2 或 4 bytes"),
        ("BACnet", "物件自帶單位、狀態旗標與名稱", "5 bytes（值本身）"),
        ("MQTT", "格式自訂，要寫進資料契約", f"{len(payload)} bytes")]
for name, meaning, size in rows:
    print(f"  {name:<7} {meaning:<20} {size}")
