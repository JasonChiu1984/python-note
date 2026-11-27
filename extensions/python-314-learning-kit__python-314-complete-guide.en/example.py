"""Python 3.14: t-strings (PEP 750) for safe SQL, deferred annotations (PEP 649), compression.zstd (needs 3.14+)."""
import annotationlib
from compression import zstd
from string.templatelib import Interpolation, Template


def to_sql(t: Template):
    """Turn a t-string into a parameterised query: every interpolation becomes ?, values travel separately."""
    sql, params = [], []
    for part in t:
        if isinstance(part, Interpolation):
            sql.append("?")
            params.append(part.value)
        else:
            sql.append(part)
    return "".join(sql), params


def poll(device: GatewayDevice) -> Reading: ...       # since 3.14 these classes need not exist yet


if __name__ == "__main__":
    name = "AHU1_SAT' OR '1'='1"
    sql, params = to_sql(t"SELECT value FROM reading WHERE point = {name} AND ts > {1795800000}")
    print("SQL:", sql)
    print("Params:", params)
    print("Annotations (as strings):", annotationlib.get_annotations(poll, format=annotationlib.Format.STRING))
    data = b"2026-11-28T10:00:00Z,AHU1_SAT,22.5\n" * 2000
    packed = zstd.compress(data)
    print(f"zstd: {len(data):,} bytes compressed below 1% of the original: {len(packed) < len(data) / 100}; round trip ok: {zstd.decompress(packed) == data}")
