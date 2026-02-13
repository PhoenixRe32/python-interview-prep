import sqlite3
from datetime import datetime, UTC
from decimal import Decimal
from typing import Protocol
from models import Order

class OrderRepository(Protocol):
    def save(self, order: Order, total: Decimal, original_json: str) -> str:
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
