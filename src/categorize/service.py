"""Process-wide categorizer, rebuilt from the database at startup.

The learned state lives in memory only. That keeps the schema unchanged and the
prototype simple: history in Postgres is the source of truth, and a restart
replays it. The tradeoff is that corrections made this session are folded into
the model on the next boot rather than persisted as their own artifact.
"""

from __future__ import annotations

import threading

from .categorizer import Categorizer, Prediction

# Database imports stay inside the functions so the categorizer itself can be
# imported (and evaluated against CSVs) without Postgres running.

_categorizer: Categorizer | None = None
_lock = threading.Lock()


def _load_all_transactions() -> list[object]:
    """Every categorized transaction, oldest first."""
    from psycopg2.extensions import connection, cursor

    from db.connection import get_connection
    from entities import Transaction

    conn: connection
    cur: cursor
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT transaction_date, amount, description, transaction_type,
                       category_id, transaction_code
                FROM transactions
                WHERE category_id IS NOT NULL
                ORDER BY transaction_date;
                """
            )
            return [
                Transaction(
                    transaction_date=str(txn_date),
                    amount=float(amount),
                    description=desc,
                    transaction_type=ttype,
                    category_id=cid,
                    transaction_code=code,
                )
                for txn_date, amount, desc, ttype, cid, code in cur.fetchall()
            ]


def get_categorizer() -> Categorizer:
    """Return the shared categorizer, training it on first use.

    Double-checked under a lock so two concurrent requests during a cold start
    don't each pay for a full fit.
    """
    global _categorizer
    if _categorizer is None:
        with _lock:
            if _categorizer is None:
                from queries import get_categories

                _categorizer = Categorizer().fit(
                    _load_all_transactions(), get_categories()
                )
    return _categorizer


def reload_categorizer() -> Categorizer:
    """Force a full retrain from the database. Safe to call at any time."""
    global _categorizer
    with _lock:
        from queries import get_categories

        _categorizer = Categorizer().fit(_load_all_transactions(), get_categories())
    return _categorizer


def suggest(
    description: str | None,
    transaction_code: str | None = None,
) -> Prediction:
    """Predict a category for one transaction."""
    return get_categorizer().predict(description, transaction_code)


def record_correction(
    description: str | None,
    transaction_code: str | None,
    category_id: int,
    transaction_date: object = None,
) -> None:
    """Teach the categorizer from a category the user chose or fixed.

    Call this from the create/update transaction handlers. It takes effect on
    the very next prediction.
    """
    get_categorizer().learn(
        description=description,
        transaction_code=transaction_code,
        category_id=category_id,
        transaction_date=transaction_date,
        corrected=True,
    )
