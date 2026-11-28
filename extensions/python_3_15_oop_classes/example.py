"""設備類別階層：C3 MRO、Protocol 結構型別與 ABC 的差異（需 Python 3.10+；3.15 可加上 disjoint_base 標註）。"""
import sys
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class Readable(Protocol):
    def read(self) -> float: ...


class Device(ABC):
    @abstractmethod
    def read(self) -> float: ...

    def describe(self):
        return f"{type(self).__name__} -> {self.read()}"


class ModbusMixin:
    def describe(self):
        return "Modbus:" + super().describe()


class LoggingMixin:
    def describe(self):
        return "Log:" + super().describe()


class Meter(LoggingMixin, ModbusMixin, Device):
    def read(self):
        return 123.4


class ThirdPartySensor:              # 沒有繼承任何東西，但有 read()
    def read(self):
        return 21.7


if __name__ == "__main__":
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    print("MRO：", " → ".join(c.__name__ for c in Meter.__mro__))
    print("describe()：", Meter().describe())
    s = ThirdPartySensor()
    print("ThirdPartySensor 是 Readable：", isinstance(s, Readable), "；是 Device：", isinstance(s, Device))
    try:
        Device()
    except TypeError as e:
        print("直接建立抽象類別：", type(e).__name__)
    try:
        type("Bad", (ModbusMixin, LoggingMixin, Meter), {})
    except TypeError as e:
        print("不一致的 MRO：", str(e).split("\n")[0])
    import typing
    print("typing.disjoint_base 可用：", hasattr(typing, "disjoint_base"))
