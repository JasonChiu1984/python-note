"""進階技巧組合：描述器做欄位驗證、__init_subclass__ 自動註冊驅動、contextvars 傳遞請求 ID（標準函式庫）。"""
import contextvars

request_id = contextvars.ContextVar("request_id", default="-")


class Bounded:
    """描述器：設定屬性時檢查範圍，錯誤訊息帶欄位名稱。"""

    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi

    def __set_name__(self, owner, name):
        self.name = "_" + name

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        if not self.lo <= value <= self.hi:
            raise ValueError(f"[{request_id.get()}] {self.name[1:]}={value} 超出 {self.lo}–{self.hi}")
        setattr(obj, self.name, value)


DRIVERS = {}


class Driver:
    protocol = None

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if cls.protocol:
            DRIVERS[cls.protocol] = cls          # 定義子類別時自動註冊

    setpoint = Bounded(5.0, 15.0)


class ModbusDriver(Driver):
    protocol = "modbus"


class BacnetDriver(Driver):
    protocol = "bacnet"


if __name__ == "__main__":
    print("已註冊驅動：", sorted(DRIVERS))
    for rid, proto, sp in (("req-001", "modbus", 7.5), ("req-002", "bacnet", 25.0)):
        token = request_id.set(rid)
        try:
            d = DRIVERS[proto]()
            d.setpoint = sp
            print(f"[{request_id.get()}] {proto} setpoint = {d.setpoint}")
        except ValueError as e:
            print("拒絕：", e)
        finally:
            request_id.reset(token)
    print("請求結束後的 request_id：", request_id.get())
