"""Python 3.12: PEP 695 generics and type aliases, itertools.batched, more flexible f-strings (needs 3.12+)."""
from dataclasses import dataclass
from itertools import batched

type Address = int                       # the type statement: an explicit alias


@dataclass(frozen=True)
class Reading[T]:                        # no TypeVar or Generic[T] boilerplate
    point: str
    value: T


def latest[T](items: list[Reading[T]]) -> Reading[T]:
    return items[-1]


if __name__ == "__main__":
    addrs: list[Address] = list(range(0, 250))
    plans = [(b[0], len(b)) for b in batched(addrs, 125)]     # Modbus reads at most 125 registers at once
    print("Read plan (start address, count):", plans)
    temps = [Reading("SAT", 22.4), Reading("SAT", 22.6)]
    modes = [Reading("MODE", "cooling")]
    print("Latest temperature:", latest(temps), "; latest mode:", latest(modes))
    point = {"name": "SAT", "unit": "°C"}
    print(f"The unit of {point["name"]} is {point["unit"]}")  # 3.12 allows the same quotes inside f-strings
    print("Underlying type of Address:", Address.__value__)
