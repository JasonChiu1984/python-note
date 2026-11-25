from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Reading:
    sensor_id: str
    celsius: float

    def __post_init__(self) -> None:
        if not self.sensor_id.strip():
            raise ValueError("sensor_id must not be blank")
        if not isfinite(self.celsius):
            raise ValueError("celsius must be finite")
