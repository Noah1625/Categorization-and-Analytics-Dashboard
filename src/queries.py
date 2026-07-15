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


def spending_by_category() -> list[tuple[str, float]]:
    """Total spend per expense category (JOIN + GROUP BY), highest first."""
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.category_name, SUM(t.amount) AS total
                FROM transactions t
                JOIN categories c ON c.category_id = t.category_id
                WHERE c.transaction_class = 'Expense'
                GROUP BY c.category_name
                ORDER BY total DESC;
                """
            )
            return [(str(name), float(total)) for name, total in cur.fetchall()]


def total_spending() -> float:
    conn: connection
    cur: cursor

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(t.amount), 0)
                FROM transactions t
                JOIN categories c
                    ON t.category_id = c.category_id
                WHERE c.transaction_class = 'Expense';
                """
            )

            total, = cur.fetchone()

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