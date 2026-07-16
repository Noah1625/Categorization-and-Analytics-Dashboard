import argparse
import sys
from collections.abc import Callable
from psycopg2.extensions import connection, cursor
from db.connection import get_config, get_connection
from queries import budget_vs_actual, get_categories, get_recent_transactions, spending_by_category, spending_by_month, total_spending, budget_vs_actual, net_cash_flow_by_month
from schema import create_tables
from seed import seed


def check() -> None:
    """Confirm we can reach the database and print the server version."""
    cfg = get_config()
    print(f"Connecting to {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']} ...")
    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            row = cur.fetchone()
            print(row[0] if row else "unknown")
    print("Connection OK.")


def setup() -> None:
    """Create the tables (if missing) and seed them (if empty)."""
    create_tables()
    seed()


def demo() -> None:
    """Run the example queries from queries.py and print their results."""
    print("Categories:")
    for c in get_categories()[:5]:
        print(f"  {c.category_id:>2}  {c.category_name} ({c.transaction_class})")

    print("\nMost recent transactions:")
    for t in get_recent_transactions(5):
        print(f"  {t.transaction_date}  {t.amount:>10.2f}  {t.description}")

    print("\nTotal spending by category (expenses):")
    for name, total in spending_by_category()[:10]:
        print(f"  {name:<24} {total:>12.2f}")

    print("\nTotal spending by month (expenses):")
    for month, total in spending_by_month():
        print(f"  {month:<10} {total:>12.2f}")

    print("\nTotal historical spending:")
    print(f"  ${total_spending():,.2f}")

    print("\nBudget vs Actual:")
    for category, budget, actual, remaining in budget_vs_actual("2018-07"):
        print(
            f"{category:<25} | "
            f"Budget: {budget:>8.2f} | "
            f"Actual: {actual:>8.2f} | "
            f"Remaining: {remaining:>8.2f}"
        )

    print("\nMonthly Cash Flow:")
    for month, income, expense, net in net_cash_flow_by_month():
        print(
            f"{month} | Income: ${income:>8.2f} | "
            f"Expenses: ${expense:>8.2f} | "
            f"Net: ${net:>8.2f}"
        )


COMMANDS: dict[str, Callable[[], None]] = {
    "check": check,
    "setup": setup,
    "demo": demo,
}


def main() -> None:
    """Parse the command line and run the requested task."""
    parser = argparse.ArgumentParser(description="Analytics dashboard database tasks.")
    parser.add_argument("command", choices=COMMANDS.keys(), help="task to run")
    args = parser.parse_args()

    try:
        COMMANDS[args.command]()
    except Exception as exc:
        print(f"Error running '{args.command}': {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
