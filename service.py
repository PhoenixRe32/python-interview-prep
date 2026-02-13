from datetime import datetime, UTC
from typing import Any
from models import Order
from pricing import PricingCalculator
from repository import OrderRepository
from notifications import EmailSender

class OrderService:
    def __init__(
        self,
        calculator: PricingCalculator,
        repository: OrderRepository,
        email_sender: EmailSender
    ):
        self.calculator = calculator
        self.repository = repository
        self.email_sender = email_sender

    def process(self, order_json: str, coupon: str | None = None) -> dict[str, Any]:
        try:
            order = Order.from_json(order_json)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

        total = self.calculator.calculate(order, coupon)

        try:
            created_at = self.repository.save(order, total, order_json)
            ok = True
            err = None
        except ValueError as e:
            ok = False
            err = str(e)
            created_at = datetime.now(UTC).isoformat()

        if ok:
            try:
                self.email_sender.send_confirmation(order, total)
            except Exception:
                pass

        return {
            "ok": ok,
            "order_id": order.id,
            "total": float(total),
            "created_at": created_at,
            "error": err,
        }
