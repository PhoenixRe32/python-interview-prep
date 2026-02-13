import unittest
from decimal import Decimal
from models import Order, Customer, OrderItem
from pricing import PricingCalculator

class TestPricingCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = PricingCalculator()
        self.customer = Customer(email="test@example.com", vip=False)
        self.items = [
            OrderItem(sku="ABC", qty=2, unit_price=Decimal("12.5")),
            OrderItem(sku="XYZ", qty=1, unit_price=Decimal("99.0"))
        ]
        self.order = Order(id="o-123", customer=self.customer, items=self.items, country="IE")

    def test_calculate_subtotal(self):
        # 2 * 12.5 + 1 * 99.0 = 124.0
        total = self.calculator.calculate(self.order)
        # Subtotal 124, Shipping 0, Tax 124 * 0.23 = 28.52. Total = 152.52
        self.assertEqual(total, Decimal("152.52"))

    def test_calculate_with_shipping(self):
        # Low subtotal
        items = [OrderItem(sku="ABC", qty=1, unit_price=Decimal("10.0"))]
        order = Order(id="o-low", customer=self.customer, items=items, country="IE")
        # Subtotal 10, Shipping 7.99, Tax (17.99 * 0.23) = 4.1377 -> 4.14. Total = 22.13
        total = self.calculator.calculate(order)
        self.assertEqual(total, Decimal("22.13"))

    def test_calculate_non_ie_uk_shipping(self):
        order = Order(id="o-intl", customer=self.customer, items=self.items, country="US")
        # Subtotal 124, Shipping 12.0, Tax (136.0 * 0.2) = 27.2. Total = 163.2
        total = self.calculator.calculate(order)
        self.assertEqual(total, Decimal("163.20"))

    def test_vip_discount(self):
        customer = Customer(email="vip@example.com", vip=True)
        order = Order(id="o-vip", customer=customer, items=self.items, country="IE")
        # Subtotal 124, Shipping 0, Tax 28.52. Total before discount 152.52
        # VIP discount: 152.52 * 0.9 = 137.268 -> 137.27
        total = self.calculator.calculate(order)
        self.assertEqual(total, Decimal("137.27"))

    def test_coupon_save10(self):
        # Subtotal 124, Shipping 0, Tax 28.52. Total before discount 152.52
        # Coupon SAVE10: 152.52 - 10 = 142.52
        total = self.calculator.calculate(self.order, coupon="SAVE10")
        self.assertEqual(total, Decimal("142.52"))

if __name__ == "__main__":
    unittest.main()
