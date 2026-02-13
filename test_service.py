import unittest
from decimal import Decimal
from typing import Any
from business import Order, Customer, OrderItem, OrderService, PricingCalculator

class FakeOrderRepository:
    def __init__(self):
        self.orders = {}
        self.saved_total = None

    def save(self, order: Order, total: Decimal, original_json: str) -> str:
        if order.id in self.orders:
            raise ValueError("Order already exists")
        self.orders[order.id] = order
        self.saved_total = total
        return "2026-02-13T19:00:00Z"

class FakeEmailSender:
    def __init__(self):
        self.sent_to = None
        self.sent_total = None

    def send_confirmation(self, order: Order, total: Decimal) -> None:
        self.sent_to = order.customer.email
        self.sent_total = total

class TestOrderService(unittest.TestCase):
    def setUp(self):
        self.calculator = PricingCalculator()
        self.repo = FakeOrderRepository()
        self.email = FakeEmailSender()
        self.service = OrderService(self.calculator, self.repo, self.email)

    def test_process_order_calls_repo_and_email(self):
        order_json = """
        {
            "id": "o-123",
            "customer": {"email": "test@example.com", "vip": false},
            "items": [{"sku": "ABC", "qty": 1, "unit_price": 100.0}],
            "country": "IE"
        }
        """
        # Subtotal 100, Shipping 0, Tax 23. Total 123
        result = self.service.process(order_json)

        self.assertTrue(result["ok"])
        self.assertEqual(self.repo.saved_total, Decimal("123.00"))
        self.assertEqual(self.email.sent_to, "test@example.com")
        self.assertEqual(self.email.sent_total, Decimal("123.00"))

    def test_process_duplicate_order(self):
        order_json = '{"id": "dup", "customer": {"email": "a@b.com"}, "items": [{"sku":"X", "qty":1, "unit_price":10}]}'
        self.service.process(order_json)
        result = self.service.process(order_json)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Order already exists")

if __name__ == "__main__":
    unittest.main()
