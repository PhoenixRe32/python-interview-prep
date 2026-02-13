# Python 3.12+
from __future__ import annotations
import os
from typing import Any

from bootstrap import get_order_service

def process_order(order_json: str, coupon: str | None = None) -> dict[str, Any]:
    """
    Legacy entry point.
    """
    service = get_order_service()
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