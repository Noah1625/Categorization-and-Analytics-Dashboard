import argparse
import sys
from collections.abc import Callable
from psycopg2.extensions import connection, cursor
from db.connection import get_config, get_connection
from queries import get_categories, get_recent_transactions, spending_by_category
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
