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