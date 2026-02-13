# Python 3.12+
from __future__ import annotations
import os
from typing import Any

from models import Order
from pricing import PricingCalculator
from repository import SQLiteOrderRepository
from notifications import SMTPEmailSender
from service import OrderService

def process_order(order_json: str, coupon: str | None = None) -> dict[str, Any]:
    """
    Legacy entry point.
    """
    calculator = PricingCalculator()
    repo = SQLiteOrderRepository(os.getenv("ORDERS_DB", "orders.db"))
    email_sender = SMTPEmailSender(
        smtp_host=os.getenv("SMTP_HOST", "localhost"),
        smtp_port=int(os.getenv("SMTP_PORT", "25")),
        sender_email=os.getenv("SENDER_EMAIL", "no-reply@example.com"),
        enabled=os.getenv("SEND_EMAILS", "true").lower() == "true"
    )

    service = OrderService(calculator, repo, email_sender)
    return service.process(order_json, coupon)

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