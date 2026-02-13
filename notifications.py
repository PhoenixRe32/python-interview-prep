import smtplib
from decimal import Decimal
from email.message import EmailMessage
from typing import Protocol
from models import Order

class EmailSender(Protocol):
    def send_confirmation(self, order: Order, total: Decimal) -> None:
        ...


class SMTPEmailSender:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        enabled: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.enabled = enabled

    def send_confirmation(self, order: Order, total: Decimal) -> None:
        if not self.enabled:
            return

        msg = EmailMessage()
        msg["From"] = self.sender_email
        msg["To"] = order.customer.email
        msg["Subject"] = f"Order {order.id} confirmation"
        msg.set_content(f"Thanks! Your total is {total}.")

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
            s.send_message(msg)
