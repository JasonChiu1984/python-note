from __future__ import annotations

from .domain import OrderLine
from .repository import InMemoryOrderRepository
from .service import OrderService


def main() -> None:
    service = OrderService(InMemoryOrderRepository())
    order = service.place_order(
        customer_id="plant-a",
        idempotency_key="demo-order-001",
        lines=[
            OrderLine(sku="SENSOR-TEMP", quantity=2, unit_price_cents=1250),
            OrderLine(sku="GATEWAY-IO", quantity=1, unit_price_cents=8900),
        ],
    )
    print(f"order={order.id} total_cents={order.total_cents}")


if __name__ == "__main__":
    main()
