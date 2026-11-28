"""Python 3.12：PEP 695 泛型語法與 type 別名、itertools.batched 分批讀取、更彈性的 f-string（需 Python 3.12+）。"""
from dataclasses import dataclass
from itertools import batched

type Address = int                       # type 陳述式：清楚的型別別名


@dataclass(frozen=True)
class Reading[T]:                        # 不必再寫 TypeVar 與 Generic[T]
    point: str
    value: T


def latest[T](items: list[Reading[T]]) -> Reading[T]:
    return items[-1]


if __name__ == "__main__":
    addrs: list[Address] = list(range(0, 250))
    plans = [(b[0], len(b)) for b in batched(addrs, 125)]     # Modbus 單次最多讀 125 個暫存器
    print("分批讀取計畫（起始位址, 數量）：", plans)
    temps = [Reading("SAT", 22.4), Reading("SAT", 22.6)]
    modes = [Reading("MODE", "cooling")]
    print("最新溫度：", latest(temps), "；最新模式：", latest(modes))
    point = {"name": "SAT", "unit": "°C"}
    print(f"{point["name"]} 的單位是 {point["unit"]}")    # 3.12 起 f-string 內可重用相同引號
    print("Address 的實際型別：", Address.__value__)
