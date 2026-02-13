# python-interview-prep

This document provides a detailed mapping of the changes made to the order processing system, categorized by the specific programming principles and best practices they address.

---

### 1. SOLID Principles

#### **SRP: Single Responsibility Principle**
The original monolithic `process_order` function was broken down into specialized components, each with a single reason to change:
*   **`models.py` (`Order.from_json`)**: Now exclusively handles **Parsing and Validation**. It ensures data integrity before the business logic starts.
*   **`pricing.py` (`PricingCalculator`)**: Encapsulates all **Financial Rules**. Changes to tax rates, shipping logic, or discount tiers only affect this class.
*   **`repository.py` (`SQLiteOrderRepository`)**: Dedicated to **Persistence**. It manages the database connection and the SQL-specific details of saving an order.
*   **`notifications.py` (`SMTPEmailSender`)**: Responsible only for **Communication**. It handles the formatting and delivery of emails via SMTP.
*   **`service.py` (`OrderService`)**: Acts as a **Process Orchestrator**. It coordinates the flow between the parser, calculator, repository, and notifier without knowing their internal details.

#### **DIP: Dependency Inversion Principle**
High-level business logic no longer depends on low-level implementation details:
*   **Protocols**: Introduced `OrderRepository` and `EmailSender` as Python `Protocols` (static duck typing).
*   **Dependency Injection**: `OrderService` accepts these protocols in its constructor. This allowed us to swap the real SQLite database and SMTP server for an `InMemoryOrderRepository` and `FakeEmailSender` during testing, making the tests fast and reliable.

#### **OCP: Open/Closed Principle**
*   **Architectural Level**: The system is **open for extension** through the use of `Protocols` and `Dependency Injection`. New persistence layers or notification channels can be added without modifying the core `OrderService`.
*   **Pragmatic Implementation**: Volatile business logic (like coupons in `PricingCalculator`) is isolated into specific methods. This creates a "seam" that is easy to extend in the future (e.g., by refactoring to a Strategy pattern) while keeping the current implementation simple and readable.

---

### 2. Clean Code & KISS (Keep It Simple, Stupid)

#### **Explanatory Methods and Encapsulation**
*   **Descriptive Naming**: Replaced generic logic with named methods like `_apply_coupon` in the `PricingCalculator`. This makes the code self-documenting; the reader sees "what" is happening (applying a coupon) without being immediately bogged down in "how" (regex or string parsing).
*   **Seams for Testing**: We avoided heavy frameworks or complex inheritance. Instead, we used simple "seams" (constructor injection) that provide just enough flexibility for testing and future expansion.

#### **Composition Root**
*   **`bootstrap.py`**: Introduced a centralized location (`get_order_service`) to wire the application together. This keeps "creation logic" separate from "execution logic," preventing configuration code (like `os.getenv`) from leaking into the business service.

---

### 3. Python Best Practices

#### **Financial Precision**
*   **`Decimal` over `float`**: Switched all money-related fields to `decimal.Decimal`. This prevents floating-point rounding errors (e.g., `0.1 + 0.2 != 0.3`) which are unacceptable in financial applications.
*   **Controlled Rounding**: Used `.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` to ensure consistent and standard currency rounding.

#### **Data Integrity**
*   **Dataclasses**: Used `@dataclass(frozen=True)` for `Order`, `Customer`, and `OrderItem`. This provides:
    *   **Immutability**: Ensures data doesn't change unexpectedly during processing.
    *   **Clarity**: Replaced opaque dictionaries (`order["items"][0]["price"]`) with structured objects (`order.items[0].unit_price`).
*   **Type Hinting**: Added comprehensive type hints (`-> Decimal`, `order: Order`) to enable better IDE support and catch potential bugs via static analysis (Mypy).

#### **Modern Standards**
*   **UTC-Aware Timestamps**: Replaced deprecated `datetime.utcnow()` with `datetime.now(UTC)` to ensure the system is timezone-aware and compliant with modern Python standards.
*   **Context Managers**: Used `with sqlite3.connect(...)` and `with smtplib.SMTP(...)` to ensure resources are always properly closed, even if an error occurs.

---

### 4. TDD (Test-Driven Development) & YAGNI

*   **Small, Verifiable Commits**: Each change was accompanied by a test run. We maintained the legacy `test_business.py` as a "Gold Master" integration test while adding granular unit tests (`test_pricing.py`, `test_service.py`) for the new components.
*   **YAGNI (You Ain't Gonna Need It)**: We avoided over-engineering. For example, we didn't implement a complex plugin system for coupons; we used a simple, extendable method within the calculator that meets the current requirements.