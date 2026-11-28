"""外部 payload（TypedDict）→ 驗證 → 內部領域物件（frozen dataclass），並收集所有錯誤一次回報（標準函式庫）。"""
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict, get_type_hints


class PointPayload(TypedDict):          # 外部系統送來的形狀，欄位可能缺漏、型別可能錯
    name: str
    addr: int
    datatype: Literal["int16", "uint16", "float32"]
    scale: NotRequired[float]


@dataclass(frozen=True, slots=True)
class Point:                             # 內部只接受已驗證、單位明確的物件
    name: str
    addr: int
    datatype: str
    scale: float


ALLOWED_TYPES = {"int16", "uint16", "float32"}


def to_domain(raw: dict) -> Point:
    errors = []
    hints = get_type_hints(PointPayload)
    for key in ("name", "addr", "datatype"):
        if key not in raw:
            errors.append(f"缺少 {key}")
    unknown = set(raw) - set(hints)
    if unknown:
        errors.append(f"未知欄位 {sorted(unknown)}")
    if "addr" in raw and (not isinstance(raw["addr"], int) or isinstance(raw["addr"], bool) or not 0 <= raw["addr"] <= 65535):
        errors.append(f"addr 必須是 0–65535 的整數，收到 {raw['addr']!r}")
    if "datatype" in raw and raw["datatype"] not in ALLOWED_TYPES:
        errors.append(f"datatype 必須是 {sorted(ALLOWED_TYPES)}，收到 {raw['datatype']!r}")
    scale = raw.get("scale", 1.0)
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or scale == 0:
        errors.append(f"scale 必須是非零數值，收到 {scale!r}")
    if errors:
        raise ValueError("；".join(errors))
    return Point(raw["name"], raw["addr"], raw["datatype"], float(scale))


if __name__ == "__main__":
    samples = [
        {"name": "SAT", "addr": 0, "datatype": "int16", "scale": 0.1},
        {"name": "KW", "addr": 100, "datatype": "float32"},
        {"name": "RAT", "addr": "1", "datatype": "int32", "units": "degC"},
        {"addr": True, "datatype": "uint16", "scale": 0},
    ]
    for raw in samples:
        try:
            print("OK  ", to_domain(raw))
        except ValueError as e:
            print("FAIL", e)
