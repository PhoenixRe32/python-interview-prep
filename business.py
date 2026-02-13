# Python 3.12+
from __future__ import annotations

import json
import os
import smtplib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC
from decimal import Decimal, ROUND_HALF_UP
from email.message import EmailMessage
from typing import Any


@dataclass(frozen=True)
class Customer:
    email: str
    vip: bool


@dataclass(frozen=True)
class OrderItem:
    sku: str
    qty: int
    unit_price: Decimal


@dataclass(frozen=True)
class Order:
    id: str
    customer: Customer
    items: list[OrderItem]
    country: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Order:
        customer_data = data["customer"]
        customer = Customer(
            email=customer_data["email"],
            vip=customer_data.get("vip", False)
        )
        items = [
            OrderItem(
                sku=it["sku"],
                qty=it["qty"],
                unit_price=Decimal(str(it["unit_price"]))
            )
            for it in data["items"]
        ]
        return cls(
            id=data["id"],
            customer=customer,
            items=items,
            country=data.get("country", "IE")
        )

    @classmethod
    def from_json(cls, order_json: str) -> Order:
        try:
            data = json.loads(order_json)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON") from e

        if "id" not in data:
            raise ValueError("Missing id")
        if "items" not in data or not data["items"]:
            raise ValueError("No items")
        if "customer" not in data or "email" not in data["customer"]:
            raise ValueError("Missing customer email")

        return cls.from_dict(data)


class PricingCalculator:
    def calculate(self, order: Order, coupon: str | None = None) -> Decimal:
        subtotal = sum((it.qty * it.unit_price for it in order.items), Decimal("0.0"))

        shipping = Decimal("0.0")
        if subtotal < Decimal("50"):
            shipping = Decimal("7.99")
        if order.country not in ("IE", "UK"):
            shipping += Decimal("12.0")

        tax_rate = Decimal("0.23") if order.country == "IE" else Decimal("0.2")
        tax = (subtotal + shipping) * tax_rate

        total = subtotal + shipping + tax

        if order.customer.vip:
            total *= Decimal("0.9")

        if coupon:
            total = self._apply_coupon(total, coupon)

        total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return max(total, Decimal("0.0"))

    def _apply_coupon(self, total: Decimal, coupon: str) -> Decimal:
        if coupon == "SAVE10":
            return total - Decimal("10")
        if coupon == "HALF":
            return total * Decimal("0.5")
        if coupon.startswith("PCT"):
            try:
                pct = int(coupon[3:])
                return total * (Decimal("100") - Decimal(pct)) / Decimal("100")
            except ValueError:
                pass
        return total


def process_order(order_json: str, coupon: str | None = None) -> dict[str, Any]:
    """
    Takes JSON like:
      {"id":"o-123","customer":{"email":"a@b.com","vip":false},
       "items":[{"sku":"ABC","qty":2,"unit_price":12.5},{"sku":"XYZ","qty":1,"unit_price":99.0}],
       "country":"IE"}
    """
    # parse input
    try:
        order = Order.from_json(order_json)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    # business logic: pricing
    calculator = PricingCalculator()
    total = calculator.calculate(order, coupon)

    # persistence (SQLite) - env config mixed here
    db_path = os.getenv("ORDERS_DB", "orders.db")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # schema management mixed in runtime path
    cur.execute(
        "CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, payload TEXT, total REAL, created_at TEXT)"
    )

    created_at = datetime.now(UTC).isoformat()
    try:
        cur.execute(
            "INSERT INTO orders (id, payload, total, created_at) VALUES (?, ?, ?, ?)",
            (order.id, order_json, float(total), created_at),
        )
        con.commit()
        ok = True
        err = None
    except sqlite3.IntegrityError:
        ok = False
        err = "Order already exists"
    finally:
        con.close()

    # notifications (email) mixed in too
    if ok:
        if os.getenv("SEND_EMAILS", "true").lower() == "true":
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "25"))
            sender = os.getenv("SENDER_EMAIL", "no-reply@example.com")
            recipient = order.customer.email

            msg = EmailMessage()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Order {order.id} confirmation"
            msg.set_content(f"Thanks! Your total is {total}.")

            # no retries, no timeouts, no error handling
            s = smtplib.SMTP(smtp_host, smtp_port)
            s.send_message(msg)
            s.quit()

    return {
        "ok": ok,
        "order_id": order.id,
        "total": float(total),
        "created_at": created_at,
        "error": err,
    }

if __name__ == "__main__":
    example_order = """
    {
        "id": "o-123",
        "customer": {"email": "test@example.com", "vip": false},
        "items": [
            {"sku": "ABC", "qty": 2, "unit_price": 12.5},
            {"sku": "XYZ", "qty": 1, "unit_price": 99.0}
        ],
        "country": "IE"
    }
    """

    result = process_order(example_order, coupon="SAVE10")
    print(result)