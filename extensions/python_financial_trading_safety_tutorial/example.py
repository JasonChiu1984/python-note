"""委託前風控與保留額：下單時先保留資金，成交扣款、撤單釋放未成交部分；所有金額用 Decimal（教學模擬，不連任何券商）。"""
from decimal import Decimal as D


class Account:
    def __init__(self, cash):
        self.cash, self.reserved, self.orders = D(cash), D(0), {}

    @property
    def available(self):
        return self.cash - self.reserved

    def place(self, oid, qty, price, max_order_value=D("200000")):
        value = D(qty) * D(price)
        if qty <= 0 or D(price) <= 0:
            return f"{oid} 拒絕：數量與價格必須為正"
        if value > max_order_value:
            return f"{oid} 拒絕：單筆金額 {value:,} 超過上限 {max_order_value:,}"
        if value > self.available:
            return f"{oid} 拒絕：可用資金 {self.available:,} 不足 {value:,}"
        self.reserved += value
        self.orders[oid] = {"qty": qty, "price": D(price), "filled": 0}
        return f"{oid} 接受，保留 {value:,}，可用 {self.available:,}"

    def fill(self, oid, qty):
        o = self.orders[oid]
        qty = min(qty, o["qty"] - o["filled"])
        cost = D(qty) * o["price"]
        o["filled"] += qty
        self.reserved -= cost
        self.cash -= cost
        return f"{oid} 成交 {qty}，扣款 {cost:,}，現金 {self.cash:,}"

    def cancel(self, oid):
        o = self.orders[oid]
        left = o["qty"] - o["filled"]
        release = D(left) * o["price"]
        self.reserved -= release
        o["qty"] = o["filled"]
        return f"{oid} 撤單，釋放未成交 {left} 股的保留 {release:,}；已成交 {o['filled']} 股不回滾"


if __name__ == "__main__":
    acct = Account("300000")
    for step in (lambda: acct.place("A1", 100, "1050"),
                 lambda: acct.place("A2", 1000, "250"),
                 lambda: acct.place("A3", 200, "1100"),
                 lambda: acct.fill("A1", 60),
                 lambda: acct.cancel("A1"),
                 lambda: acct.place("A3", 150, "1100")):
        print(step())
    print(f"最終：現金 {acct.cash:,}、保留 {acct.reserved:,}、可用 {acct.available:,}")
    print("浮點數陷阱：0.1 + 0.2 =", 0.1 + 0.2, "；Decimal：", D("0.1") + D("0.2"))
