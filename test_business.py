import unittest
import os
import sqlite3
import json
from business import process_order

class TestBusiness(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_orders.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.environ["ORDERS_DB"] = self.db_path
        os.environ["SEND_EMAILS"] = "false"

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_process_order_success(self):
        order_json = """
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
        # Subtotal: 2 * 12.5 + 1 * 99.0 = 25.0 + 99.0 = 124.0
        # Shipping: subtotal >= 50, so 0.0. Country is IE, so no extra shipping. Total shipping = 0.0
        # Tax: (124.0 + 0.0) * 0.23 = 28.52
        # Total: 124.0 + 0.0 + 28.52 = 152.52
        # Coupon SAVE10: 152.52 - 10 = 142.52
        
        result = process_order(order_json, coupon="SAVE10")
        
        self.assertTrue(result["ok"])
        self.assertEqual(result["order_id"], "o-123")
        self.assertEqual(result["total"], 142.52)
        
        # Verify DB
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT total FROM orders WHERE id='o-123'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 142.52)
        conn.close()

    def test_process_order_vip_discount(self):
        order_json = """
        {
            "id": "o-vip",
            "customer": {"email": "vip@example.com", "vip": true},
            "items": [
                {"sku": "ABC", "qty": 1, "unit_price": 100.0}
            ],
            "country": "UK"
        }
        """
        # Subtotal: 100.0
        # Shipping: 0.0 (subtotal >= 50). Country UK: no extra shipping.
        # Tax: (100.0 + 0.0) * 0.2 = 20.0
        # Total before discounts: 120.0
        # VIP discount: 120.0 * 0.9 = 108.0
        
        result = process_order(order_json)
        self.assertEqual(result["total"], 108.0)

    def test_process_order_shipping_low_subtotal(self):
        order_json = """
        {
            "id": "o-low",
            "customer": {"email": "low@example.com", "vip": false},
            "items": [
                {"sku": "ABC", "qty": 1, "unit_price": 10.0}
            ],
            "country": "IE"
        }
        """
        # Subtotal: 10.0
        # Shipping: 7.99 (subtotal < 50). Country IE: no extra shipping.
        # Tax: (10.0 + 7.99) * 0.23 = 17.99 * 0.23 = 4.1377
        # Total: 10.0 + 7.99 + 4.1377 = 22.1277 -> rounded to 22.13
        
        result = process_order(order_json)
        self.assertEqual(result["total"], 22.13)

    def test_missing_id(self):
        result = process_order('{"items":[]}')
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Missing id")

if __name__ == "__main__":
    unittest.main()
