from collections.abc import Iterable

from .model import Reading


class ReplaySource:
    def __init__(self, readings: Iterable[Reading]) -> None:
        self._readings = iter(readings)

    def read(self) -> Reading:
        return next(self._readings)
