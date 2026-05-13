from __future__ import annotations

from collections.abc import Sequence

from .domain import Order, OrderLine, OrderValidationError
from .repository import InMemoryOrderRepository


class OrderService:
    def __init__(self, repository: InMemoryOrderRepository) -> None:
        self._repository = repository

    def place_order(
        self,
        customer_id: str,
        lines: Sequence[OrderLine],
        idempotency_key: str,
    ) -> Order:
        normalized_customer = customer_id.strip()
        normalized_key = idempotency_key.strip()
        if not normalized_customer:
            raise OrderValidationError("customer_id must not be blank")
        if not normalized_key:
            raise OrderValidationError("idempotency_key must not be blank")

        existing = self._repository.find_by_idempotency_key(normalized_key)
        if existing is not None:
            return existing

        order_lines = tuple(lines)
        self._validate_lines(order_lines)
        order = Order(
            id=self._repository.next_id(),
            customer_id=normalized_customer,
            lines=order_lines,
            idempotency_key=normalized_key,
        )
        self._repository.save(order)
        return order

    @staticmethod
    def _validate_lines(lines: tuple[OrderLine, ...]) -> None:
        if not lines:
            raise OrderValidationError("order must contain at least one line")
        for line in lines:
            if not line.sku.strip():
                raise OrderValidationError("sku must not be blank")
            if line.quantity <= 0:
                raise OrderValidationError("quantity must be positive")
            if line.unit_price_cents <= 0:
                raise OrderValidationError("unit_price_cents must be positive")
