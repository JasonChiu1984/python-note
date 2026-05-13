from __future__ import annotations

import unittest

from testing_quality_gate.domain import OrderLine, OrderValidationError
from testing_quality_gate.repository import InMemoryOrderRepository
from testing_quality_gate.service import OrderService


class OrderServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryOrderRepository()
        self.service = OrderService(self.repository)

    def test_place_order_calculates_total(self) -> None:
        order = self.service.place_order(
            customer_id="plant-a",
            idempotency_key="req-001",
            lines=[
                OrderLine(sku="sensor", quantity=2, unit_price_cents=100),
                OrderLine(sku="gateway", quantity=1, unit_price_cents=900),
            ],
        )

        self.assertEqual(order.total_cents, 1100)
        self.assertEqual(order.customer_id, "plant-a")

    def test_duplicate_idempotency_key_returns_existing_order(self) -> None:
        first = self.service.place_order(
            customer_id="plant-a",
            idempotency_key="req-001",
            lines=[OrderLine(sku="sensor", quantity=1, unit_price_cents=100)],
        )
        second = self.service.place_order(
            customer_id="plant-a",
            idempotency_key="req-001",
            lines=[OrderLine(sku="sensor", quantity=99, unit_price_cents=100)],
        )

        self.assertEqual(first, second)
        self.assertEqual(len(self.repository.all_orders()), 1)

    def test_rejects_empty_order_lines(self) -> None:
        with self.assertRaises(OrderValidationError):
            self.service.place_order("plant-a", [], "req-empty")

    def test_rejects_invalid_line_values(self) -> None:
        invalid_lines = [
            OrderLine(sku="", quantity=1, unit_price_cents=100),
            OrderLine(sku="sensor", quantity=0, unit_price_cents=100),
            OrderLine(sku="sensor", quantity=1, unit_price_cents=0),
        ]
        for line in invalid_lines:
            with self.subTest(line=line):
                with self.assertRaises(OrderValidationError):
                    self.service.place_order("plant-a", [line], f"req-{line!r}")

    def test_rejects_blank_customer_and_key(self) -> None:
        line = OrderLine(sku="sensor", quantity=1, unit_price_cents=100)
        with self.assertRaises(OrderValidationError):
            self.service.place_order("", [line], "req-blank-customer")
        with self.assertRaises(OrderValidationError):
            self.service.place_order("plant-a", [line], "")


if __name__ == "__main__":
    unittest.main()
