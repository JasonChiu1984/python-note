from __future__ import annotations

from .domain import Order


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._idempotency_index: dict[str, int] = {}
        self._next_id = 1

    def next_id(self) -> int:
        order_id = self._next_id
        self._next_id += 1
        return order_id

    def save(self, order: Order) -> None:
        self._orders[order.id] = order
        self._idempotency_index[order.idempotency_key] = order.id

    def find_by_idempotency_key(self, key: str) -> Order | None:
        order_id = self._idempotency_index.get(key)
        if order_id is None:
            return None
        return self._orders[order_id]

    def all_orders(self) -> list[Order]:
        return [self._orders[key] for key in sorted(self._orders)]
