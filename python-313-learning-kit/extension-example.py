"""Python 3.13：copy.replace() 產生修改後的不可變物件、warnings.deprecated 標記淘汰 API（需 Python 3.13+）。"""
import copy
import warnings
from dataclasses import dataclass


@dataclass(frozen=True)
class PointConfig:
    name: str
    addr: int
    scale: float = 1.0


@warnings.deprecated("read_point() 已淘汰，請改用 read_points() 批次讀取")
def read_point(cfg: PointConfig) -> float:
    return 225 * cfg.scale


def read_points(cfgs):
    return {c.name: 225 * c.scale for c in cfgs}


if __name__ == "__main__":
    sat = PointConfig("SAT", 0, 0.1)
    new = copy.replace(sat, scale=0.01)               # 適用於 dataclass、namedtuple、datetime 等
    print("原設定：", sat)
    print("新設定：", new, "；原物件不變：", sat.scale)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        read_point(sat)
        print("呼叫舊 API 的警告：", w[0].category.__name__, "-", w[0].message)
    print("新 API：", read_points([sat, new]))
