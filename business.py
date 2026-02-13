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
from typing import Any, Protocol


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


class OrderRepository(Protocol):
    def save(self, order: Order, total: Decimal, original_json: str) -> str:
        ...


class EmailSender(Protocol):
    def send_confirmation(self, order: Order, total: Decimal) -> None:
        ...


class SQLiteOrderRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, payload TEXT, total REAL, created_at TEXT)"
            )

    def save(self, order: Order, total: Decimal, original_json: str) -> str:
        created_at = datetime.now(UTC).isoformat()
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute(
                    "INSERT INTO orders (id, payload, total, created_at) VALUES (?, ?, ?, ?)",
                    (order.id, original_json, float(total), created_at),
                )
            return created_at
        except sqlite3.IntegrityError as e:
            raise ValueError("Order already exists") from e


class SMTPEmailSender:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        enabled: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.enabled = enabled

    def send_confirmation(self, order: Order, total: Decimal) -> None:
        if not self.enabled:
            return

        msg = EmailMessage()
        msg["From"] = self.sender_email
        msg["To"] = order.customer.email
        msg["Subject"] = f"Order {order.id} confirmation"
        msg.set_content(f"Thanks! Your total is {total}.")

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
            s.send_message(msg)


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

    # persistence (SQLite)
    db_path = os.getenv("ORDERS_DB", "orders.db")
    repo = SQLiteOrderRepository(db_path)

    try:
        created_at = repo.save(order, total, order_json)
        ok = True
        err = None
    except ValueError as e:
        ok = False
        err = str(e)
        created_at = datetime.now(UTC).isoformat()  # Fallback for return

    # notifications (email)
    email_sender = SMTPEmailSender(
        smtp_host=os.getenv("SMTP_HOST", "localhost"),
        smtp_port=int(os.getenv("SMTP_PORT", "25")),
        sender_email=os.getenv("SENDER_EMAIL", "no-reply@example.com"),
        enabled=os.getenv("SEND_EMAILS", "true").lower() == "true"
    )

    if ok:
        try:
            email_sender.send_confirmation(order, total)
        except Exception:
            # For now, we just skip errors as it was doing before (implicitly)
            # but ideally we should log it.
            pass

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