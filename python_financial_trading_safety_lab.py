"""Paper-only order lifecycle. Offline synthetic data; no broker integration."""
from dataclasses import dataclass
from decimal import Decimal
from datetime import UTC, datetime, timedelta
import argparse
import json
import unittest

D = Decimal
FEE_PER_UNIT = D("0.02")  # Synthetic; no fixed fee, taxes or rebates.
MAX_EXPOSURE = D("400.00")
CENT = D("0.01")
NOW = datetime(2026, 11, 25, 9, tzinfo=UTC)


def price(text):
    if not isinstance(text, str):
        raise ValueError("start from a decimal string")
    p = D(text)
    if not p.is_finite() or not D("0.01") <= p <= D("1000000"):
        raise ValueError("price out of lab range")
    if p != p.quantize(CENT):
        raise ValueError("price must match the synthetic 0.01 tick")
    return p


@dataclass
class Order:
    order_id: str
    qty: int
    limit: Decimal
    filled: int = 0
    state: str = "PENDING_ACK"


class PaperBook:
    def __init__(self):
        self.cash = D("1000.00")
        self.position = 0
        self.position_cost = D("0.00")
        self.orders = {}
        self.executions = {}
        self.blocked = False

    @staticmethod
    def active(order):
        return order.state not in {"FILLED", "CANCELED"}

    @property
    def reserved(self):
        return sum(((o.qty - o.filled) * (o.limit + FEE_PER_UNIT)
                    for o in self.orders.values() if self.active(o)), D("0.00"))

    @property
    def reserved_notional(self):
        return sum(((o.qty - o.filled) * o.limit
                    for o in self.orders.values() if self.active(o)), D("0.00"))

    def submit(self, order_id, qty, limit, observed_at, now):
        if not isinstance(order_id, str) or not order_id or type(qty) is not int or qty < 1:
            raise ValueError("expect order ID and a positive integer quantity")
        ceiling = price(limit)
        if order_id in self.orders:
            old = self.orders[order_id]
            if (old.qty, old.limit) != (qty, ceiling):
                raise ValueError("client order ID conflicts with previous intent")
            return old  # Same intent, not a new order.
        if self.blocked or any(o.state == "UNKNOWN_ACK" for o in self.orders.values()):
            raise ValueError("reconcile before accepting new orders")
        if observed_at.utcoffset() is None or now.utcoffset() is None:
            raise ValueError("timestamps require an offset")
        if not timedelta(0) <= now - observed_at <= timedelta(seconds=2):
            raise ValueError("stale or future market snapshot")
        if qty * (ceiling + FEE_PER_UNIT) > self.cash - self.reserved:
            raise ValueError("insufficient unreserved cash")
        if self.position_cost + self.reserved_notional + qty * ceiling > MAX_EXPOSURE:
            raise ValueError("cost-basis exposure cap exceeded")
        result = Order(order_id, qty, ceiling)
        self.orders[order_id] = result
        return result

    def unknown_ack(self, order_id):
        order = self.orders[order_id]
        if order.state != "PENDING_ACK":
            raise ValueError("only pending acknowledgments can time out")
        order.state = "UNKNOWN_ACK"  # Keep cash reserved.

    def confirm_open(self, order_id):
        # Only after a trusted reconciliation source says the order exists.
        order = self.orders[order_id]
        if order.state not in {"PENDING_ACK", "UNKNOWN_ACK"}:
            raise ValueError("cannot re-open an order")
        order.state = "OPEN"

    def request_cancel(self, order_id):
        order = self.orders[order_id]
        if order.state not in {"OPEN", "PARTIAL"}:
            raise ValueError("cannot request cancel in current state")
        order.state = "CANCEL_PENDING"

    def fill(self, execution_id, order_id, qty, execution_price):
        if type(qty) is not int or qty < 1:
            raise ValueError("invalid fill quantity")
        if not isinstance(execution_id, str) or not execution_id:
            raise ValueError("invalid execution ID")
        paid = price(execution_price)
        payload = (order_id, qty, paid)
        if execution_id in self.executions:
            if self.executions[execution_id] != payload:
                self.blocked = True
                raise ValueError("execution ID has contradictory payload")
            return False
        order = self.orders[order_id]
        if not self.active(order) or paid > order.limit or qty > order.qty - order.filled:
            self.blocked = True
            raise ValueError("fill contradicts current ledger; reconcile")
        order.filled += qty
        self.executions[execution_id] = payload
        self.cash -= qty * (paid + FEE_PER_UNIT)
        self.position_cost += qty * paid
        self.position += qty
        if order.filled == order.qty:
            order.state = "FILLED"
        elif order.state != "CANCEL_PENDING":
            order.state = "PARTIAL"
        return True

    def confirm_cancel(self, order_id):
        order = self.orders[order_id]
        if order.state == "FILLED":
            return  # Terminal state is not downgraded by a late response here.
        if order.state != "CANCEL_PENDING":
            raise ValueError("missing cancel request")
        order.state = "CANCELED"

    def reconcile(self, cash, position):
        if self.cash != cash or self.position != position:
            self.blocked = True
            return False
        # Matching total cash and position do not by themselves resolve
        # an UNKNOWN_ACK or clear an existing integrity hold.
        return True


def scenario():
    ledger = PaperBook()
    output = []
    order = ledger.submit("client-01", 5, "40.00", NOW, NOW)

    def snapshot(label):
        output.append({"step": label, "state": order.state, "filled": order.filled,
                       "cash": str(ledger.cash), "reserved": str(ledger.reserved),
                       "position": ledger.position})

    snapshot("收到委託")
    ledger.unknown_ack(order.order_id)
    snapshot("ACK 不明")
    ledger.confirm_open(order.order_id)
    ledger.fill("e-1", order.order_id, 2, "39.50")
    snapshot("部分成交 2")
    ledger.request_cancel(order.order_id)
    snapshot("撤單待確認")
    ledger.fill("e-2", order.order_id, 1, "39.80")
    snapshot("撤單途中再成 1")
    ledger.confirm_cancel(order.order_id)
    assert ledger.reconcile(D("881.14"), 3)
    snapshot("撤單完成／對帳")
    return output


class LabTests(unittest.TestCase):
    def test_dedup_client_and_execution(self):
        ledger = PaperBook()
        order = ledger.submit("o", 3, "20.00", NOW, NOW)
        self.assertIs(order, ledger.submit("o", 3, "20.00", NOW, NOW))
        with self.assertRaises(ValueError):
            ledger.submit("o", 4, "20.00", NOW, NOW)
        self.assertTrue(ledger.fill("e", "o", 1, "19.50"))
        self.assertFalse(ledger.fill("e", "o", 1, "19.50"))
        self.assertEqual(ledger.cash, D("980.48"))
        with self.assertRaises(ValueError):
            ledger.fill("e", "o", 1, "19.40")
        self.assertTrue(ledger.blocked)

    def test_unknown_ack_keeps_reserve_and_blocks_new_orders(self):
        ledger = PaperBook()
        order = ledger.submit("o", 3, "20.00", NOW, NOW)
        ledger.unknown_ack(order.order_id)
        self.assertEqual(ledger.reserved, D("60.06"))
        self.assertTrue(ledger.reconcile(D("1000.00"), 0))
        with self.assertRaisesRegex(ValueError, "reconcile"):
            ledger.submit("new", 1, "10.00", NOW, NOW)
        ledger.confirm_open("o")
        self.assertEqual(order.state, "OPEN")

    def test_cancel_race(self):
        rows = scenario()
        self.assertEqual(rows[-2]["state"], "CANCEL_PENDING")
        self.assertEqual(rows[-1]["filled"], 3)
        self.assertEqual(rows[-1]["cash"], "881.14")
        self.assertEqual(rows[-1]["reserved"], "0.00")

    def test_pretrade_checks(self):
        ledger = PaperBook()
        for order in [(41, "30.00", NOW, "cash"),
                      (11, "40.00", NOW, "exposure"),
                      (1, "40.00", NOW-timedelta(seconds=3), "stale"),
                      (1, "40.001", NOW, "tick"),
                      (1, "NaN", NOW, "range")]:
            qty, limit, timestamp, message = order
            with self.assertRaisesRegex(ValueError, message):
                ledger.submit("o", qty, limit, timestamp, NOW)
        self.assertEqual(ledger.orders, {})

    def test_invalid_fill_and_reconcile_freeze(self):
        ledger = PaperBook()
        ledger.submit("o", 1, "40.00", NOW, NOW)
        with self.assertRaises(ValueError):
            ledger.fill("e", "o", 2, "40.00")
        self.assertEqual((ledger.cash, ledger.position), (D("1000.00"), 0))
        self.assertFalse(ledger.reconcile(D("999.00"), 0))
        self.assertTrue(ledger.blocked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=["lab"], verbosity=2)
    else:
        print(json.dumps(scenario(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
