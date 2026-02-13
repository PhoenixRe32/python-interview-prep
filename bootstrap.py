import os
from pricing import PricingCalculator
from repository import SQLiteOrderRepository
from notifications import SMTPEmailSender
from service import OrderService

def get_order_service() -> OrderService:
    """
    Composition Root: Centralizes the creation of the application's object graph.
    New code should use this factory to get a fully configured OrderService.
    """
    calculator = PricingCalculator()
    
    db_path = os.getenv("ORDERS_DB", "orders.db")
    repo = SQLiteOrderRepository(db_path)
    
    email_sender = SMTPEmailSender(
        smtp_host=os.getenv("SMTP_HOST", "localhost"),
        smtp_port=int(os.getenv("SMTP_PORT", "25")),
        sender_email=os.getenv("SENDER_EMAIL", "no-reply@example.com"),
        enabled=os.getenv("SEND_EMAILS", "true").lower() == "true"
    )

    return OrderService(calculator, repo, email_sender)
