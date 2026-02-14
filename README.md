# python-interview-prep

This document provides a detailed mapping of the changes made to the order processing system, categorized by the specific programming principles and best practices they address.

## High level overview

At its core, the business logic handles the **automated lifecycle of a retail order**. It is designed to process an incoming order request and apply a specific set of rules to determine the final price and fulfillment steps.

Here is exactly what the business logic can do:

#### 1. **Flexible Pricing & Taxation**
The system automatically calculates the total based on the following rules:
*   **Regional Tax**: It applies a **23% tax** for orders from Ireland (`IE`) and a **20% tax** for all other countries (defaulting to the `UK` or international standards).
*   **Tiered Shipping**: 
    *   Orders under **€50** incur a base shipping fee of **€7.99**.
    *   International orders (outside `IE` and `UK`) incur an **additional €12.00** flat fee.
    *   High-value orders (over €50) within the local region get free shipping.

#### 2. **Discount & Loyalty Engine**
The logic supports multiple layers of price reductions:
*   **VIP Program**: Customers marked as `vip: true` automatically receive a **10% discount** on their entire order (calculated after tax and shipping).
*   **Coupon System**: It processes three types of promotional codes:
    *   `SAVE10`: A flat **€10 off** the total.
    *   `HALF`: A **50% reduction** of the total.
    *   `PCT[number]` (e.g., `PCT25`): A dynamic **percentage discount** (e.g., 25% off).

#### 3. **Validation & Integrity**
Before any math happens, the logic enforces "Sanity Checks":
*   **Mandatory Data**: It rejects orders missing a unique ID, a customer email, or any line items.
*   **Financial Precision**: All calculations are performed using `Decimal` arithmetic to ensure that the business never loses or gains fractions of a cent due to rounding errors (a common risk in financial software).
*   **Non-Negative Totals**: It guarantees that no combination of discounts can ever result in a negative price (the customer never gets paid to take an item).

#### 4. **Order Fulfillment Workflow**
When an order is processed, the system coordinates three distinct outcomes:
1.  **Duplicate Protection**: It checks the database and prevents the same Order ID from being processed twice.
2.  **Audit Trail**: It saves the full original JSON payload, the final calculated total, and a UTC timestamp for every successful order.
3.  **Customer Communication**: If the order is successfully saved, it triggers an automated email confirmation to the customer with their order ID and the final amount.

#### 5. **Failure Resilience**
The business logic is "fail-safe" regarding non-critical steps:
*   If the **Database** fails (e.g., duplicate order), the process stops and returns an error.
*   If the **Email** fails, the order is **still considered successful**, and the system returns the order details to the user. This prevents a temporary network glitch from losing a valid sale.