"""中級綜合練習：dataclass、生成器、上下文管理器、例外分類與日誌，一起完成「讀點位表 → 驗證 → 摘要」（標準函式庫）。"""
import csv
import io
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter

logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO, stream=__import__("sys").stdout)
log = logging.getLogger("points")

CSV_TEXT = """name,addr,scale,unit
AHU1_SAT,0,0.1,degC
AHU1_RAT,1,0.1,degC
CH1_KW,100,abc,kW
CH1_KW,101,1,kW
AHU1_DMP,70000,1,%
"""


class PointError(ValueError):
    """點位資料錯誤：可以略過該列繼續處理。"""


@dataclass(frozen=True)
class Point:
    name: str
    addr: int
    scale: float
    unit: str


def rows(text):
    yield from csv.DictReader(io.StringIO(text))        # 生成器：大檔也不會一次讀進記憶體


def parse(row, line):
    try:
        p = Point(row["name"], int(row["addr"]), float(row["scale"]), row["unit"])
    except ValueError as e:
        raise PointError(f"第 {line} 列格式錯誤：{e}") from e
    if not 0 <= p.addr <= 65535:
        raise PointError(f"第 {line} 列位址超出範圍：{p.addr}")
    return p


@contextmanager
def timed(label):
    start = perf_counter()
    try:
        yield
    finally:
        log.info("%s 完成（耗時已記錄，不印出以保持輸出可重現）", label)
        _ = perf_counter() - start


if __name__ == "__main__":
    points, seen = [], set()
    with timed("點位表驗證"):
        for line, row in enumerate(rows(CSV_TEXT), start=2):
            try:
                p = parse(row, line)
            except PointError as e:
                log.warning("%s", e)
                continue
            if p.name in seen:
                log.warning("第 %d 列名稱重複：%s", line, p.name)
                continue
            seen.add(p.name)
            points.append(p)
    by_unit = {}
    for p in points:
        by_unit.setdefault(p.unit, []).append(p.name)
    print(f"有效點位 {len(points)} 個：", by_unit)
