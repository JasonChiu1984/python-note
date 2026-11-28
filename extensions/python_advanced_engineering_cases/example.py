"""高階案例：把「輪詢 → 驗證 → 去抖動告警 → 通知」組成可測試的管線，每一段都是可替換的函式（標準函式庫）。"""
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator


@dataclass(frozen=True)
class Reading:
    t: int
    point: str
    value: float | None


def validate(rows: Iterable[Reading], lo=-20, hi=60) -> Iterator[Reading]:
    for r in rows:
        if r.value is not None and lo <= r.value <= hi:
            yield r


def debounce(rows: Iterable[Reading], limit: float, need: int) -> Iterator[tuple[int, str, str]]:
    """連續 need 筆超標才觸發、連續 need 筆正常才解除，避免在門檻附近來回跳動。"""
    state, streak = "normal", 0
    for r in rows:
        breach = r.value > limit
        streak = streak + 1 if breach == (state == "normal") else 0
        if streak >= need:
            state = "alarm" if state == "normal" else "normal"
            streak = 0
            yield r.t, r.point, state


def pipeline(source: Iterable[Reading], notify: Callable[[str], None]):
    for t, point, state in debounce(validate(source), limit=28.0, need=3):
        notify(f"t={t} {point} → {state}")


if __name__ == "__main__":
    raw = [27.8, 28.2, 27.9, 28.3, 28.4, 999, 28.6, 28.1, 27.6, 27.8, 28.1, 27.5, 27.4, 27.2]
    readings = [Reading(t, "AHU1_SAT", v) for t, v in enumerate(raw)]
    sent = []
    pipeline(readings, sent.append)
    print("原始資料：", raw)
    print("通知：", sent)
    print(f"沒有去抖動時，超過 28 °C 的跳動次數：{sum(1 for a, b in zip(raw, raw[1:]) if (a > 28) != (b > 28) and b != 999)}")
