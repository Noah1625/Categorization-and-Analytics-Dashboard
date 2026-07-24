from psycopg2.extensions import connection, cursor
from db.connection import get_connection
from entities import Category, Transaction


def get_categories() -> list[Category]:
    """Return every category, mapped to Category objects."""
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT category_id, category_name, transaction_class "
                "FROM categories ORDER BY category_id;"
            )
            return [
                Category(category_name=name, transaction_class=cls, category_id=cid)
                for cid, name, cls in cur.fetchall()
            ]


def get_recent_transactions(limit: int = 10) -> list[Transaction]:
    """Return the most recent transactions (parameterized LIMIT)."""
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            # %s placeholders are filled by psycopg2 — this is how you avoid
            # SQL injection; never build the value into the string yourself.
            cur.execute(
                """
                SELECT transaction_date, amount, description, transaction_type,
                       category_id, transaction_code
                FROM transactions
                ORDER BY transaction_date DESC, transaction_id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return [
                Transaction(
                    transaction_date=str(date),
                    amount=float(amount),
                    description=desc,
                    transaction_type=ttype,
                    category_id=cid,
                    transaction_code=code,
                )
                for date, amount, desc, ttype, cid, code in cur.fetchall()
            ]


def get_transactions_for_category(category_id: int) -> list[Transaction]:
    """Return every transaction for one category (parameterized WHERE)."""
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT transaction_date, amount, description, transaction_type,
                       category_id, transaction_code
                FROM transactions
                WHERE category_id = %s
                ORDER BY transaction_date;
                """,
                (category_id,),
            )
            return [
                Transaction(
                    transaction_date=str(date),
                    amount=float(amount),
                    description=desc,
                    transaction_type=ttype,
                    category_id=cid,
                    transaction_code=code,
                )
                for date, amount, desc, ttype, cid, code in cur.fetchall()
            ]


def spending_by_category(month: str | None = None) -> list[tuple[str, float]]:
    """Total spend per expense category."""

    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:

            if month:
                cur.execute(
                    """
                    SELECT
                        c.category_name,
                        SUM(t.amount) AS total
                    FROM transactions t
                    JOIN categories c
                        ON c.category_id = t.category_id
                    WHERE c.transaction_class = 'Expense'
                    AND TO_CHAR(t.transaction_date, 'YYYY-MM') = %s
                    GROUP BY c.category_name
                    ORDER BY total DESC;
                    """,
                    (month,),
                )

            else:
                cur.execute(
                    """
                    SELECT
                        c.category_name,
                        SUM(t.amount) AS total
                    FROM transactions t
                    JOIN categories c
                        ON c.category_id = t.category_id
                    WHERE c.transaction_class = 'Expense'
                    GROUP BY c.category_name
                    ORDER BY total DESC;
                    """
                )

            return [
                (str(name), float(total))
                for name, total in cur.fetchall()
            ]


def total_spending(month: str | None = None) -> float:
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:

            if month:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM transactions t
                    JOIN categories c
                        ON t.category_id = c.category_id
                    WHERE c.transaction_class = 'Expense'
                    AND TO_CHAR(t.transaction_date, 'YYYY-MM') = %s;
                    """,
                    (month,),
                )
            else:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM transactions t
                    JOIN categories c
                        ON t.category_id = c.category_id
                    WHERE c.transaction_class = 'Expense';
                    """
                )

            result = cur.fetchone()
            total = result[0] if result else 0.0

            return float(total)

def spending_by_month() -> list[tuple[str, float]]:
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    TO_CHAR(t.transaction_date, 'YYYY-MM') AS month,
                    SUM(t.amount) AS total_spending
                FROM transactions t
                JOIN categories c
                    ON t.category_id = c.category_id
                WHERE c.transaction_class = 'Expense'
                GROUP BY month
                ORDER BY month;
                """
            )

            return [(str(month), float(total)) for month, total in cur.fetchall()]
        

def budget_vs_actual(month: str) -> list[tuple[str, float, float, float]]:
    """Compare monthly budgets against actual spending for a given month."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.category_name,
                    b.monthly_budget,
                    COALESCE(SUM(t.amount), 0) AS actual_spending,
                    b.monthly_budget - COALESCE(SUM(t.amount), 0) AS remaining_budget
                FROM budgets b
                JOIN categories c
                    ON b.category_id = c.category_id
                LEFT JOIN transactions t
                    ON b.category_id = t.category_id
                    AND TO_CHAR(t.transaction_date, 'YYYY-MM') = %s
                WHERE c.transaction_class = 'Expense'
                GROUP BY
                    c.category_name,
                    b.monthly_budget
                ORDER BY c.category_name;
                """,
                (month,),
            )

            return [
                (
                    str(category),
                    float(budget),
                    float(actual),
                    float(remaining),
                )
                for category, budget, actual, remaining in cur.fetchall()
            ]
        

def net_cash_flow_by_month() -> list[tuple[str, float, float, float]]:
    """Return monthly income, expenses, and net cash flow."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH monthly_totals AS (
                    SELECT
                        TO_CHAR(t.transaction_date, 'YYYY-MM') AS month,
                        SUM(
                            CASE
                                WHEN c.transaction_class = 'Income'
                                THEN t.amount
                                ELSE 0
                            END
                        ) AS total_income,
                        SUM(
                            CASE
                                WHEN c.transaction_class = 'Expense'
                                THEN t.amount
                                ELSE 0
                            END
                        ) AS total_expense
                    FROM transactions t
                    JOIN categories c
                        ON t.category_id = c.category_id
                    GROUP BY
                        TO_CHAR(t.transaction_date, 'YYYY-MM')
                )
                SELECT
                    month,
                    total_income,
                    total_expense,
                    total_income - total_expense AS net_cash_flow
                FROM monthly_totals
                ORDER BY month;
                """
            )

            return [
                (
                    str(month),
                    float(income),
                    float(expense),
                    float(net),
                )
                for month, income, expense, net in cur.fetchall()
            ]
        
def _transaction_filters(
    start_date: str | None,
    end_date: str | None,
    category_ids: list[int] | None,
    min_amount: float | None,
    max_amount: float | None,
    search: str | None,
) -> tuple[str, list[object]]:
    """Build the shared WHERE clause for the transactions list + its count.

    Returns the SQL (starting with WHERE, or empty when nothing is filtered)
    and the matching parameter list. Values always go in as placeholders.
    """
    clauses: list[str] = []
    params: list[object] = []

    if start_date:
        clauses.append("t.transaction_date >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("t.transaction_date <= %s")
        params.append(end_date)
    if category_ids:
        clauses.append("t.category_id = ANY(%s)")
        params.append(category_ids)
    if min_amount is not None:
        clauses.append("t.amount >= %s")
        params.append(min_amount)
    if max_amount is not None:
        clauses.append("t.amount <= %s")
        params.append(max_amount)
    if search:
        clauses.append("(t.description ILIKE %s OR t.transaction_code ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def search_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    category_ids: list[int] | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Return one page of transactions matching the filters, newest first."""
    conn: connection
    cur: cursor

    where, params = _transaction_filters(
        start_date, end_date, category_ids, min_amount, max_amount, search
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    t.transaction_id,
                    t.transaction_date,
                    t.amount,
                    t.description,
                    t.transaction_type,
                    t.category_id,
                    c.category_name,
                    c.transaction_class,
                    t.is_user_created
                FROM transactions t
                LEFT JOIN categories c
                    ON c.category_id = t.category_id
                {where}
                ORDER BY t.transaction_date DESC, t.transaction_id DESC
                LIMIT %s OFFSET %s;
                """,
                (*params, limit, offset),
            )

            return [
                {
                    "transaction_id": tid,
                    "transaction_date": str(date),
                    "amount": float(amount),
                    "description": desc,
                    "transaction_type": ttype,
                    "category_id": cid,
                    "category_name": cname,
                    "transaction_class": cclass,
                    "is_user_created": bool(user_created),
                }
                for tid, date, amount, desc, ttype, cid, cname, cclass, user_created
                in cur.fetchall()
            ]


def count_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    category_ids: list[int] | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    search: str | None = None,
) -> int:
    """Total number of transactions matching the filters (drives pagination)."""
    conn: connection
    cur: cursor

    where, params = _transaction_filters(
        start_date, end_date, category_ids, min_amount, max_amount, search
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN categories c
                    ON c.category_id = t.category_id
                {where};
                """,
                tuple(params),
            )
            result = cur.fetchone()
            return int(result[0]) if result else 0


def get_transaction(transaction_id: int) -> dict[str, object] | None:
    """Return a single transaction (with its category), or None if missing."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    t.transaction_id,
                    t.transaction_date,
                    t.amount,
                    t.description,
                    t.transaction_type,
                    t.category_id,
                    c.category_name,
                    c.transaction_class,
                    t.is_user_created
                FROM transactions t
                LEFT JOIN categories c
                    ON c.category_id = t.category_id
                WHERE t.transaction_id = %s;
                """,
                (transaction_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    tid, date, amount, desc, ttype, cid, cname, cclass, user_created = row
    return {
        "transaction_id": tid,
        "transaction_date": str(date),
        "amount": float(amount),
        "description": desc,
        "transaction_type": ttype,
        "category_id": cid,
        "category_name": cname,
        "transaction_class": cclass,
        "is_user_created": bool(user_created),
    }


def create_transaction(
    transaction_date: str,
    amount: float,
    description: str,
    category_id: int | None = None,
) -> int:
    """Insert a user-created transaction and return its new id."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            if category_id is None:
                cur.execute(
                    """
                    INSERT INTO transactions
                        (transaction_date, amount, description, transaction_type,
                         category_id, transaction_code, is_user_created)
                    VALUES (%s, %s, %s, 'debit', NULL, NULL, TRUE)
                    RETURNING transaction_id;
                    """,
                    (transaction_date, amount, description),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO transactions
                        (transaction_date, amount, description, transaction_type,
                         category_id, transaction_code, is_user_created)
                    SELECT
                        %s, %s, %s,
                        CASE WHEN c.transaction_class = 'Income' THEN 'credit'
                             ELSE 'debit' END,
                        c.category_id, NULL, TRUE
                    FROM categories c
                    WHERE c.category_id = %s
                    RETURNING transaction_id;
                    """,
                    (transaction_date, amount, description, category_id),
                )
            result = cur.fetchone()
            if result is None:
                raise ValueError(f"No category with id {category_id}")
            conn.commit()
            return int(result[0])


def set_transaction_category(transaction_id: int, category_id: int) -> bool:
    """Assign a category to one transaction, leaving its other fields alone."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE transactions t
                SET category_id      = c.category_id,
                    transaction_type = CASE
                        WHEN c.transaction_class = 'Income' THEN 'credit'
                        ELSE 'debit' END
                FROM categories c
                WHERE t.transaction_id = %s
                  AND t.is_user_created
                  AND c.category_id = %s;
                """,
                (transaction_id, category_id),
            )
            changed = cur.rowcount
            conn.commit()
            return changed > 0


def update_transaction(
    transaction_id: int,
    transaction_date: str,
    amount: float,
    description: str,
    category_id: int | None = None,
) -> bool:
    """Update a transaction. Returns False for seeded (read-only) rows."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            if category_id is None:
                cur.execute(
                    """
                    UPDATE transactions t
                    SET transaction_date = %s,
                        amount           = %s,
                        description      = %s,
                        category_id      = NULL,
                        transaction_type = 'debit'
                    WHERE t.transaction_id = %s
                      AND t.is_user_created;
                    """,
                    (transaction_date, amount, description, transaction_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE transactions t
                    SET transaction_date = %s,
                        amount           = %s,
                        description      = %s,
                        category_id      = c.category_id,
                        transaction_type = CASE
                            WHEN c.transaction_class = 'Income' THEN 'credit'
                            ELSE 'debit' END
                    FROM categories c
                    WHERE t.transaction_id = %s
                      AND t.is_user_created
                      AND c.category_id = %s;
                    """,
                    (transaction_date, amount, description, transaction_id, category_id),
                )
            changed = cur.rowcount
            conn.commit()
            return changed > 0


def delete_transaction(transaction_id: int) -> bool:
    """Delete a transaction. Returns False for seeded (read-only) rows."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM transactions "
                "WHERE transaction_id = %s AND is_user_created;",
                (transaction_id,),
            )
            changed = cur.rowcount
            conn.commit()
            return changed > 0


def available_months() -> list[str]:
    """Return months available in transaction history."""
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT
                    TO_CHAR(transaction_date, 'YYYY-MM') AS month
                FROM transactions
                ORDER BY month;
                """
            )

            return [str(month) for (month,) in cur.fetchall()]