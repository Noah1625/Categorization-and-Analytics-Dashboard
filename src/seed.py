import csv
import os
from psycopg2.extensions import connection, cursor
from psycopg2.extras import execute_values # pyright: ignore[reportUnknownVariableType]
from db.connection import get_connection
from entities import Budget, Category, Transaction

# CSVs live at {repo}/data/processed relative to this file (src/).
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _load_categories() -> list[Category]:
    return [
        Category(
            category_name=row["category_name"],
            transaction_class=row["transaction_class"],
            category_id=int(row["category_id"]),
        )
        for row in _read_csv("categories.csv")
    ]


def _load_budgets() -> list[Budget]:
    return [
        Budget(
            category_name=row["category_name"],
            monthly_budget=float(row["monthly_budget"]),
            category_id=int(row["category_id"]),
        )
        for row in _read_csv("budgets.csv")
    ]


def _load_transactions() -> list[Transaction]:
    return [
        Transaction(
            transaction_date=row["transaction_date"],
            amount=float(row["amount"]),
            description=row["description"],
            transaction_type=row["transaction_type"],
            category_id=int(row["category_id"]),
            transaction_code=row["transaction_code"],
        )
        for row in _read_csv("transactions.csv")
    ]


def _is_empty(cur: cursor, table: str) -> bool:
    cur.execute(f"SELECT 1 FROM {table} LIMIT 1;")
    return cur.fetchone() is None


def seed() -> None:
    """Insert the CSV data, skipping any table that is already populated."""
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            if _is_empty(cur, "categories"):
                categories = _load_categories()
                execute_values(
                    cur,
                    "INSERT INTO categories (category_id, category_name, transaction_class) VALUES %s",
                    [(c.category_id, c.category_name, c.transaction_class) for c in categories],
                )
                print(f"Seeded {len(categories)} categories.")
            else:
                print("categories already populated, skipping.")

            if _is_empty(cur, "budgets"):
                budgets = _load_budgets()
                execute_values(
                    cur,
                    "INSERT INTO budgets (category_id, category_name, monthly_budget) VALUES %s",
                    [(b.category_id, b.category_name, b.monthly_budget) for b in budgets],
                )
                print(f"Seeded {len(budgets)} budgets.")
            else:
                print("budgets already populated, skipping.")

            if _is_empty(cur, "transactions"):
                transactions = _load_transactions()
                execute_values(
                    cur,
                    """INSERT INTO transactions
                       (transaction_date, amount, description, transaction_type, category_id, transaction_code)
                       VALUES %s""",
                    [
                        (
                            t.transaction_date,
                            t.amount,
                            t.description,
                            t.transaction_type,
                            t.category_id,
                            t.transaction_code,
                        )
                        for t in transactions
                    ],
                )
                print(f"Seeded {len(transactions)} transactions.")
            else:
                print("transactions already populated, skipping.")
        conn.commit()


if __name__ == "__main__":
    seed()
