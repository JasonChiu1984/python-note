"""不可變設備設定：dataclass(frozen, slots) ＋ frozendict 欄位 ＋ sentinel 預設值，並以 CSV 往返驗證。需 Python 3.15。"""
import csv
import io
from dataclasses import dataclass, field, replace

UNSET = sentinel("UNSET")


@dataclass(frozen=True, slots=True)
class Point:
    name: str
    addr: int
    scale: float = 1.0
    tags: frozendict = field(default_factory=frozendict)
    alarm_high: float | None = None

    def __post_init__(self):
        if not 0 <= self.addr <= 65535:
            raise ValueError(f"{self.name}: 位址 {self.addr} 超出 0–65535")


def with_changes(p: Point, *, scale=UNSET, alarm_high=UNSET) -> Point:
    """只改有傳入的欄位；None 代表「清除告警上限」，UNSET 代表「不變」。"""
    changes = {k: v for k, v in (("scale", scale), ("alarm_high", alarm_high)) if v is not UNSET}
    return replace(p, **changes)


if __name__ == "__main__":
    sat = Point("SAT", 0, 0.1, frozendict(unit="degC", ahu="AHU-01"), alarm_high=30.0)
    print(sat)
    print("改倍率：", with_changes(sat, scale=0.01).scale, "；清除告警：", with_changes(sat, alarm_high=None).alarm_high,
          "；不傳：", with_changes(sat).alarm_high)
    try:
        sat.scale = 1.0
    except AttributeError as e:
        print("直接修改：", type(e).__name__)
    print("可當字典鍵：", {sat: "已部署"}[Point("SAT", 0, 0.1, frozendict(ahu="AHU-01", unit="degC"), 30.0)])

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["name", "addr", "scale", "unit", "alarm_high"])
    w.writerow([sat.name, sat.addr, sat.scale, sat.tags["unit"], "" if sat.alarm_high is None else sat.alarm_high])
    w.writerow(["RAT", 70000, 0.1, "degC", ""])
    buf.seek(0)
    for row in csv.DictReader(buf):
        try:
            p = Point(row["name"], int(row["addr"]), float(row["scale"]), frozendict(unit=row["unit"]),
                      float(row["alarm_high"]) if row["alarm_high"] else None)
            print("匯入成功：", p.name, p.addr, p.alarm_high)
        except ValueError as e:
            print("匯入失敗：", e)
