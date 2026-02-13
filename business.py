# Python 3.12+
from __future__ import annotations

import json
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage


def process_order(order_json: str, coupon: str | None = None) -> dict:
    """
    Takes JSON like:
      {"id":"o-123","customer":{"email":"a@b.com","vip":false},
       "items":[{"sku":"ABC","qty":2,"unit_price":12.5},{"sku":"XYZ","qty":1,"unit_price":99.0}],
       "country":"IE"}
    """
    # parse input
    order = json.loads(order_json)

    # basic validation (incomplete / inconsistent)
    if "id" not in order:
        return {"ok": False, "error": "Missing id"}
    if "items" not in order or not order["items"]:
        return {"ok": False, "error": "No items"}
    if "customer" not in order or "email" not in order["customer"]:
        return {"ok": False, "error": "Missing customer email"}

    # business logic: pricing + tax + discounts (all mixed in)
    subtotal = 0.0
    for it in order["items"]:
        if "qty" not in it or "unit_price" not in it:
            continue  # silently skip bad items
        subtotal += float(it["qty"]) * float(it["unit_price"])

    # shipping rules
    shipping = 0.0
    if subtotal < 50:
        shipping = 7.99
    if order.get("country") not in ("IE", "UK"):
        shipping += 12.0

    # tax rules (hard-coded, simplistic)
    tax_rate = 0.23 if order.get("country") == "IE" else 0.2
    tax = (subtotal + shipping) * tax_rate

    total = subtotal + shipping + tax

    # discounts: VIP and coupon (weird interactions)
    if order["customer"].get("vip") is True:
        total *= 0.9  # 10% off
    if coupon:
        if coupon == "SAVE10":
            total -= 10
        elif coupon == "HALF":
            total *= 0.5
        elif coupon.startswith("PCT"):
            # PCT15 -> 15%
            try:
                pct = int(coupon[3:])
                total *= (100 - pct) / 100
            except ValueError:
                pass

    # round and ensure not negative
    total = round(total, 2)
    if total < 0:
        total = 0.0

    # persistence (SQLite) - env config mixed here
    db_path = os.getenv("ORDERS_DB", "orders.db")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # schema management mixed in runtime path
    cur.execute(
        "CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, payload TEXT, total REAL, created_at TEXT)"
    )

    created_at = datetime.utcnow().isoformat()
    try:
        cur.execute(
            "INSERT INTO orders (id, payload, total, created_at) VALUES (?, ?, ?, ?)",
            (order["id"], order_json, total, created_at),
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
            recipient = order["customer"]["email"]

            msg = EmailMessage()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Order {order['id']} confirmation"
            msg.set_content(f"Thanks! Your total is {total}.")

            # no retries, no timeouts, no error handling
            s = smtplib.SMTP(smtp_host, smtp_port)
            s.send_message(msg)
            s.quit()

    return {
        "ok": ok,
        "order_id": order["id"],
        "total": total,
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