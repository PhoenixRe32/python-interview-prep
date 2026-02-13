# Interview Topics & Discussion Points

This document outlines potential interview questions and discussion points based on the refactored order processing system. It is designed to help candidates demonstrate depth in architectural thinking, Python best practices, and production-readiness.

---

### 1. Error Handling & Domain Modeling
**Question:** "I noticed you used `ValueError` for both JSON parsing and duplicate orders. Why might you want to use custom exceptions instead?"

**Answer:** 
Using generic exceptions like `ValueError` makes it difficult for calling code to react differently to different types of failures. Custom exceptions (Domain Exceptions) allow us to:
1. **Categorize Errors**: Distinguish between "Client Errors" (invalid data) and "System Errors" (database down).
2. **Clean UI/API responses**: A web framework can catch `OrderNotFoundError` and return a `404`, while a `DatabaseConnectionError` might trigger a `503`.
3. **Rich Metadata**: Custom exceptions can carry extra context (e.g., the specific field that failed validation).

**Implementation Details:**
In the current code, `Order.from_json` and `SQLiteOrderRepository.save` both raise `ValueError`. 
*   **Suggested Change**: Create a `domain/exceptions.py` with `class BusinessError(Exception): pass`, then `class DuplicateOrderError(BusinessError): pass`, etc.

---

### 2. Side Effects & Reliability
**Question:** "In `OrderService.process`, if the email fails, you just `pass`. Is this acceptable? How would you make this more robust?"

**Answer:**
It depends on the business requirement. If the email is "nice to have," a silent failure prevents the whole transaction from failing. However, for a better system:
1. **Logging**: At minimum, we should log the error so we know emails are failing.
2. **Outbox Pattern**: Save the "email task" to the database in the same transaction as the order. A separate worker then sends it. This ensures that if the order is saved, the email *will* eventually be sent.
3. **Retries**: Use a library like `tenacity` or a background queue (Celery/RQ) to retry the email sending with exponential backoff.

**Implementation Details:**
Currently, `OrderService.process` lines 37-40 use a generic `try/except Exception: pass`. 
*   **Discussion Point**: Discuss the trade-offs between "Synchronous success" vs "Eventual consistency."

---

### 3. Precision and Financial Logic
**Question:** "Why did you choose `Decimal` over `float` for the prices? Are there any downsides?"

**Answer:**
Floats use binary floating-point representation (Base-2), which cannot accurately represent many decimal fractions (like 0.1). This leads to cumulative rounding errors (e.g., `0.1 + 0.2 != 0.3`). `Decimal` uses Base-10 and offers exact precision.
*   **Downsides**: `Decimal` is slower than `float` and uses more memory. It also requires explicit handling (you can't easily mix `float` and `Decimal` in operations). However, for financial data, accuracy is non-negotiable.

**Implementation Details:**
The code uses `Decimal` throughout `pricing.py` and `models.py`. It also uses `.quantize()` with `ROUND_HALF_UP` to ensure consistent 2-decimal rounding.

---

### 4. Dependency Management (Composition Root)
**Question:** "What is the benefit of the `bootstrap.py` file? Why not just instantiate the repository inside the `OrderService`?"

**Answer:**
Instantiating dependencies inside a class creates "Hard Dependencies," making the class impossible to unit test without a real database. `bootstrap.py` acts as the **Composition Root**.
1. **Centralized Config**: All `os.getenv` calls are in one place.
2. **Switchability**: We can change the repository implementation (e.g., from SQLite to Postgres) in one line without touching the business logic.
3. **Clean Service**: The `OrderService` stays focused on *how to process an order*, not *how to connect to a database*.

**Implementation Details:**
`bootstrap.py` encapsulates the "wiring" of the system. It builds the graph: `Calculator` + `Repo` + `Sender` -> `OrderService`.

---

### 5. Idempotency
**Question:** "If the user clicks 'Submit' twice and the first request times out but actually succeeded in the DB, what happens on the second request?"

**Answer:**
The system should be **Idempotent**. In our current implementation, the `SQLiteOrderRepository` has a unique constraint on the Order ID.
1. The second request will fail with an "Order already exists" error.
2. This is good because it prevents duplicate charges/shipments.
3. **Improvement**: Instead of returning an error, a truly idempotent API might return the *existing* order result with a "200 OK" to indicate "I've already done this for you."

**Implementation Details:**
The `orders` table has `id TEXT PRIMARY KEY`. The `save` method catches `sqlite3.IntegrityError` and raises a `ValueError`.

---

### 6. Boundary Validation (Always Valid Entities)
**Question:** "How do you ensure that an `OrderItem` never has a negative quantity?"

**Answer:**
By enforcing invariants at the boundary. 
1. **Validation in Constructor**: Use dataclass `__post_init__` to validate fields.
2. **Type Safety**: Using `int` for `qty` and `Decimal` for `unit_price`.
3. **The 'Always Valid' Rule**: We should never be able to instantiate an `Order` object that is in an invalid state.

**Implementation Details:**
Currently, validation is in `Order.from_json`. 
*   **Suggested Change**: Move logic like `if self.qty <= 0: raise ValueError` into `OrderItem.__post_init__`.

---

### 7. Performance & Scaling
**Question:** "If we suddenly get 10,000 orders per minute, where will the bottleneck be?"

**Answer:**
1. **SMTP**: Sending emails synchronously is very slow (network I/O). This will block the service.
2. **SQLite**: While fast, it handles concurrent writes poorly (database locking).
3. **Solution**: Move the email sending to a background queue. Switch to a client-server database like PostgreSQL. Use an async framework (FastAPI/AnyIO) if the system is I/O bound.
