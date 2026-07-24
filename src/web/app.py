"""Flask + HTMX sample app.

Run from the ``src/`` directory:

    flask --app web.app run --debug
    # or
    python -m web.app

Then open http://127.0.0.1:5000/.
"""

from __future__ import annotations

import calendar
from datetime import date

from flask import Flask, render_template, request

from web.sample_data import CATEGORIES, TRANSACTIONS, DemoTransaction, add_transaction

from queries import (
    available_months,
    total_spending,
    spending_by_category,
    spending_by_month,
    budget_vs_actual,
    net_cash_flow_by_month,
    get_categories,
    search_transactions,
    count_transactions,
    get_transaction,
    create_transaction,
    update_transaction,
    delete_transaction,
    set_transaction_category,
)
from categorize import record_correction, suggest

PAGE_SIZE = 50

app = Flask(__name__)


@app.get("/")
def index():
    """The component showcase / style-guide landing page."""
    return render_template(
        "index.html",
        categories=CATEGORIES,
        transactions=TRANSACTIONS,
    )

@app.get("/dashboard")
def dashboard():

    months = available_months()
    selected_month = months[-1] if months else None

    return render_template(
        "dashboard.html",
        total_spending=total_spending(selected_month),
        category_spending=spending_by_category(selected_month),
        budget_data=budget_vs_actual(selected_month) if selected_month else None,
        monthly_spending=spending_by_month(),
        monthly_cash_flow=net_cash_flow_by_month(),
        months=months,
        selected_month=selected_month,
    )
    
    
@app.get("/dashboard/filter")
def dashboard_filter():

    month = request.args.get("month") or None

    return render_template(
        "partials/_dashboard_content.html",
        total_spending=total_spending(month),
        category_spending=spending_by_category(month),
        budget_data=budget_vs_actual(month) if month else None,
    )

# --- Transactions --------------------------------------------------------
# The page renders the filter form + the list; every interaction after that
# (filtering, paging, add, edit, delete) swaps a partial back in via HTMX.


def _default_range() -> tuple[str, str]:
    """First/last day of the default month for the date-range filter.

    The seeded dataset is historical, so "current month" means the most recent
    month that actually has transactions — today's month is only used when the
    table is empty. Swap ``months[-1]`` for ``date.today()`` to make it literal.
    """
    months = available_months()
    month = months[-1] if months else date.today().strftime("%Y-%m")
    year, mon = int(month[:4]), int(month[5:7])
    return f"{month}-01", f"{month}-{calendar.monthrange(year, mon)[1]:02d}"


def _float_or_none(raw: str | None) -> float | None:
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _read_filters(default_start: str | None = None,
                  default_end: str | None = None) -> dict[str, object]:
    """Pull the filter values out of the query string.

    Defaults apply only when the key is *absent* — once the filter form has
    been submitted an empty date means the user deliberately cleared it.
    ``request.values`` covers both the query string (GET filter/paging) and the
    form body (the add form, which hx-includes the filters).
    """
    args = request.values
    return {
        "start_date": args.get("start_date", default_start) or None,
        "end_date": args.get("end_date", default_end) or None,
        "category_ids": [int(c) for c in args.getlist("category") if c.isdigit()],
        "min_amount": _float_or_none(args.get("min_amount")),
        "max_amount": _float_or_none(args.get("max_amount")),
        "search": args.get("search", "").strip() or None,
    }


def _attach_suggestions(rows: list[dict[str, object]]) -> None:
    """Add a ``suggestion`` to every uncategorized row, in place."""
    for row in rows:
        if row.get("category_id") is not None:
            row["suggestion"] = None
            continue
        prediction = suggest(
            description=str(row.get("description") or ""),
            transaction_code=None,
        )
        row["suggestion"] = prediction if prediction.category_id is not None else None


def _list_context(filters: dict[str, object]) -> dict[str, object]:
    """Everything the list partial needs: the page of rows + paging state."""
    page = max(1, int(request.values.get("page", 1) or 1))
    total = count_transactions(**filters)  # pyright: ignore[reportArgumentType]
    pages = max(1, -(-total // PAGE_SIZE))  # ceil
    page = min(page, pages)

    rows = search_transactions(
        limit=PAGE_SIZE,
        offset=(page - 1) * PAGE_SIZE,
        **filters,  # pyright: ignore[reportArgumentType]
    )
    _attach_suggestions(rows)
    return {
        "transactions": rows,
        "categories": get_categories(),
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": PAGE_SIZE,
    }


@app.get("/transactions")
def transactions():
    """Full page: filter form, add form, and the first page of the list."""
    default_start, default_end = _default_range()
    filters = _read_filters(default_start, default_end)
    return render_template(
        "transactions.html",
        filters=filters,
        **_list_context(filters),
    )


@app.get("/transactions/list")
def transactions_list():
    """The filtered/paged list on its own — the HTMX swap target."""
    filters = _read_filters()
    return render_template(
        "partials/_transaction_list.html",
        filters=filters,
        **_list_context(filters),
    )


@app.post("/transactions/new")
def transactions_create():
    """Add a transaction, then re-render the list so it lands in place."""
    form = request.form
    raw_category = form.get("category_id", "").strip()
    category_id = int(raw_category) if raw_category else None
    description = form.get("description", "").strip() or "Untitled"
    amount = abs(float(form.get("amount", 0) or 0))

    create_transaction(
        transaction_date=form.get("transaction_date", "").strip(),
        amount=amount,
        description=description,
        category_id=category_id,
    )
    # A category picked by hand is a training signal too, not just a correction
    # of something we got wrong.
    if category_id is not None:
        record_correction(
            description=description,
            transaction_code=None,
            category_id=category_id,
        )
    filters = _read_filters()
    return render_template(
        "partials/_transaction_list.html",
        filters=filters,
        **_list_context(filters),
    )


@app.post("/transactions/<int:transaction_id>/categorize")
def transactions_categorize(transaction_id: int):
    """Accept a suggested category (or an override), and learn from it."""
    raw_category = request.form.get("category_id", "").strip()
    if not raw_category:
        return "", 400

    if not set_transaction_category(transaction_id, int(raw_category)):
        t = get_transaction(transaction_id)
        if t is None:
            return "", 404
        _attach_suggestions([t])
        return render_template("partials/_transaction_item.html", t=t, categories=get_categories()), 403

    t = get_transaction(transaction_id)
    if t is None:
        return "", 404

    # Whether they took the suggestion or overrode it, this is the ground truth.
    record_correction(
        description=str(t["description"] or ""),
        transaction_code=None,
        category_id=int(raw_category),
        transaction_date=t["transaction_date"],
    )
    _attach_suggestions([t])
    return render_template("partials/_transaction_item.html", t=t, categories=get_categories())


@app.get("/transactions/<int:transaction_id>/edit")
def transactions_edit_form(transaction_id: int):
    """Swap one row into an inline edit form (user-created rows only)."""
    t = get_transaction(transaction_id)
    if t is None:
        return "", 404
    if not t["is_user_created"]:
        _attach_suggestions([t])
        return render_template("partials/_transaction_item.html", t=t, categories=get_categories()), 403
    return render_template(
        "partials/_transaction_edit.html", t=t, categories=get_categories()
    )


@app.get("/transactions/<int:transaction_id>")
def transactions_row(transaction_id: int):
    """The read-only row — used to cancel out of the edit form."""
    t = get_transaction(transaction_id)
    if t is None:
        return "", 404
    _attach_suggestions([t])
    return render_template("partials/_transaction_item.html", t=t, categories=get_categories())


@app.post("/transactions/<int:transaction_id>")
def transactions_update(transaction_id: int):
    """Save an inline edit and swap the read-only row back in."""
    form = request.form
    description = form.get("description", "").strip() or "Untitled"
    amount = abs(float(form.get("amount", 0) or 0))
    raw_category = form.get("category_id", "").strip()
    category_id = int(raw_category) if raw_category else None
    update_transaction(
        transaction_id=transaction_id,
        transaction_date=form.get("transaction_date", "").strip(),
        amount=amount,
        description=description,
        category_id=category_id,
    )
    t = get_transaction(transaction_id)
    if t is None:
        return "", 404
    # An edit that set a category is the strongest signal there is. Clearing
    # one teaches nothing — the user is saying "not yet", not "not this".
    if category_id is not None:
        record_correction(
            description=description,
            transaction_code=None,
            category_id=category_id,
            transaction_date=t["transaction_date"],
        )
    _attach_suggestions([t])
    return render_template("partials/_transaction_item.html", t=t, categories=get_categories())


@app.delete("/transactions/<int:transaction_id>")
def transactions_delete(transaction_id: int):
    """Remove a user-created transaction; seeded rows are left alone."""
    if not delete_transaction(transaction_id):
        t = get_transaction(transaction_id)
        if t is None:
            return "", 404
        _attach_suggestions([t])
        return render_template("partials/_transaction_item.html", t=t, categories=get_categories()), 403

    filters = _read_filters()
    return render_template(
        "partials/_transaction_list.html",
        filters=filters,
        **_list_context(filters),
    )


# --- HTMX demo endpoints -------------------------------------------------
# Each returns an HTML *fragment* (a partial), not a whole page. HTMX swaps
# the fragment into the DOM. State is passed back and forth in the form so
# these stay stateless (except the transactions list, which is intentionally
# kept in memory so added rows stick around).


@app.post("/demo/counter")
def demo_counter():
    """Increment/decrement a value. Current value + step arrive in the form."""
    value = int(request.form.get("value", 0))
    step = int(request.form.get("step", 0))
    return render_template("partials/_counter.html", value=value + step)


@app.post("/demo/budget")
def demo_budget():
    """Recompute a budget progress bar from a new 'spent' amount."""
    limit = float(request.form.get("limit", 500))
    spent = max(0.0, float(request.form.get("spent", 0)))
    return render_template("partials/_budget.html", limit=limit, spent=spent)


@app.post("/demo/transactions")
def demo_add_transaction():
    """Add a transaction and return just the new table row to prepend."""
    category = request.form.get("category", CATEGORIES[0])
    # Income only from Paycheck in this simple demo; everything else is spend.
    transaction_class = "Income" if category == "Paycheck" else "Expense"
    t = DemoTransaction(
        date=request.form.get("date", "").strip() or "2018-07-15",
        description=request.form.get("description", "").strip() or "Untitled",
        category=category,
        transaction_class=transaction_class,
        amount=abs(float(request.form.get("amount", 0) or 0)),
    )
    add_transaction(t)
    return render_template("partials/_transaction_row.html", t=t)

@app.get("/dashboard/budget")
def dashboard_budget():
    month = request.args.get("month") or None

    return render_template(
        "partials/_budget_chart.html",
        budget_data=budget_vs_actual(month) if month else None,
    )


if __name__ == "__main__":
    app.run(debug=True)
