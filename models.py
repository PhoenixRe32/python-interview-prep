from __future__ import annotations
import json
from dataclasses import dataclass
from decimal import Decimal
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
