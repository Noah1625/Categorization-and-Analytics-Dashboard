"""In-memory sample data for the web demo.

This lets the sample page run without a database connection. When the real
pages are built, these helpers get replaced by calls into ``queries.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DemoTransaction:
    date: str
    description: str
    category: str
    transaction_class: str  # "Expense" | "Income" | "Transfer"
    amount: float


# A handful of categories mirroring data/processed/categories.csv.
CATEGORIES: list[str] = [
    "Groceries",
    "Restaurants",
    "Gas & Fuel",
    "Shopping",
    "Utilities",
    "Entertainment",
    "Paycheck",
    "Mortgage & Rent",
]

# Seeded demo transactions. Newest first (this is a plain module-level list, so
# rows added through the demo form persist for the life of the process).
TRANSACTIONS: list[DemoTransaction] = [
    DemoTransaction("2018-07-14", "Whole Foods Market", "Groceries", "Expense", 86.40),
    DemoTransaction("2018-07-13", "Shell Oil", "Gas & Fuel", "Expense", 41.10),
    DemoTransaction("2018-07-12", "Monthly Paycheck", "Paycheck", "Income", 2650.00),
    DemoTransaction("2018-07-11", "Thai Restaurant", "Restaurants", "Expense", 24.22),
    DemoTransaction("2018-07-10", "Amazon", "Shopping", "Expense", 63.99),
]


def add_transaction(t: DemoTransaction) -> None:
    """Prepend a transaction so the newest shows first."""
    TRANSACTIONS.insert(0, t)
