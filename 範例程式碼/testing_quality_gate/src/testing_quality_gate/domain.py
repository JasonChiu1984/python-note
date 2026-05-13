from __future__ import annotations

from dataclasses import dataclass


class OrderValidationError(ValueError):
    """Raised when an order violates a business rule."""


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price_cents: int

    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents


@dataclass(frozen=True)
class Order:
    id: int
    customer_id: str
    lines: tuple[OrderLine, ...]
    idempotency_key: str

    @property
    def total_cents(self) -> int:
        return sum(line.total_cents() for line in self.lines)
