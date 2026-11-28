"""Python 3.13: copy.replace() for modified copies of immutable objects, warnings.deprecated for retiring APIs (needs 3.13+)."""
import copy
import warnings
from dataclasses import dataclass


@dataclass(frozen=True)
class PointConfig:
    name: str
    addr: int
    scale: float = 1.0


@warnings.deprecated("read_point() is deprecated; use read_points() for batch reads")
def read_point(cfg: PointConfig) -> float:
    return 225 * cfg.scale


def read_points(cfgs):
    return {c.name: 225 * c.scale for c in cfgs}


if __name__ == "__main__":
    sat = PointConfig("SAT", 0, 0.1)
    new = copy.replace(sat, scale=0.01)               # works for dataclasses, namedtuples, datetime, ...
    print("Original:", sat)
    print("Modified:", new, "; original unchanged:", sat.scale)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        read_point(sat)
        print("Warning from the old API:", w[0].category.__name__, "-", w[0].message)
    print("New API:", read_points([sat, new]))
