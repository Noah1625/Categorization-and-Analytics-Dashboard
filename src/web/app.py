"""Flask + HTMX sample app.

Run from the ``src/`` directory:

    flask --app web.app run --debug
    # or
    python -m web.app

Then open http://127.0.0.1:5000/.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from web.sample_data import CATEGORIES, TRANSACTIONS, DemoTransaction, add_transaction

from queries import (
    available_months,
    total_spending,
    spending_by_category,
    spending_by_month,
    budget_vs_actual,
    net_cash_flow_by_month,
)

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

    selected_month = None

    return render_template(
        "dashboard.html",
        total_spending=total_spending(selected_month),
        category_spending=spending_by_category(selected_month),
        monthly_spending=spending_by_month(),
        monthly_cash_flow=net_cash_flow_by_month(),
        months=months,
    )
    
    


@app.get("/transactions")
def transactions():
    """Placeholder — the transactions list + add form will live here."""
    return render_template("transactions.html")


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
    budget_data = budget_vs_actual("2018-07")

    return render_template(
        "partials/_budget_chart.html",
        budget_data=budget_data,
    )


if __name__ == "__main__":
    app.run(debug=True)
