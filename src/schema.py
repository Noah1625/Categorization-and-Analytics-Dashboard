from psycopg2.extensions import connection, cursor
from db.connection import get_connection

CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS categories (
        category_id       INTEGER PRIMARY KEY,
        category_name     TEXT NOT NULL,
        transaction_class TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS budgets (
        category_id    INTEGER PRIMARY KEY REFERENCES categories (category_id),
        category_name  TEXT NOT NULL,
        monthly_budget NUMERIC(10, 2) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id   SERIAL PRIMARY KEY,
        transaction_date DATE NOT NULL,
        amount           NUMERIC(10, 2) NOT NULL,
        description      TEXT,
        transaction_type TEXT,
        category_id      INTEGER REFERENCES categories (category_id),
        transaction_code TEXT
    );
    """,
]


def create_tables() -> None:
    """Create the tables if they don't already exist."""
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            for statement in CREATE_STATEMENTS:
                cur.execute(statement)
        conn.commit()
    print("Tables ready (created if missing).")


if __name__ == "__main__":
    create_tables()
