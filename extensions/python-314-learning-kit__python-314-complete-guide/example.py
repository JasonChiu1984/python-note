"""Python 3.14：t-string（PEP 750）安全組 SQL、延遲求值的型別註解（PEP 649）、compression.zstd（需 Python 3.14+）。"""
import annotationlib
from compression import zstd
from string.templatelib import Interpolation, Template


def to_sql(t: Template):
    """把 t-string 轉成參數化查詢：插值一律變成 ?，值另外傳遞。"""
    sql, params = [], []
    for part in t:
        if isinstance(part, Interpolation):
            sql.append("?")
            params.append(part.value)
        else:
            sql.append(part)
    return "".join(sql), params


def poll(device: GatewayDevice) -> Reading: ...       # 3.14 起不需要先定義這兩個類別


if __name__ == "__main__":
    name = "AHU1_SAT' OR '1'='1"
    sql, params = to_sql(t"SELECT value FROM reading WHERE point = {name} AND ts > {1795800000}")
    print("SQL：", sql)
    print("參數：", params)
    print("註解（字串形式）：", annotationlib.get_annotations(poll, format=annotationlib.Format.STRING))
    data = b"2026-11-28T10:00:00Z,AHU1_SAT,22.5\n" * 2000
    packed = zstd.compress(data)
    print(f"zstd：{len(data):,} bytes 壓縮後不到原大小的 1%：{len(packed) < len(data) / 100}，解壓還原：{zstd.decompress(packed) == data}")
