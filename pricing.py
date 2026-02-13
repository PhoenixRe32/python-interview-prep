from decimal import Decimal, ROUND_HALF_UP
from models import Order

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
