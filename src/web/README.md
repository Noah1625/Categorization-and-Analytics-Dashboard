# Web (Flask + HTMX)

A small Flask app that serves the shared **component / style guide** page and a
few live HTMX demos. It runs on its own with in-memory sample data - no database
required - so it's a safe sandbox for agreeing on the look and feel before the
real Dashboard and Transactions pages get built.

## Run

From the `src/` directory (with the project venv active and
`pip install -r ../requirements.txt` done):

```bash
flask --app web.app run --debug
# or
python -m web.app
```

Then open <http://127.0.0.1:5000/>.

## What's here

```
web/
  app.py                 # Flask routes: the pages + HTMX fragment endpoints
  sample_data.py         # In-memory demo data (component page only)
  static/css/styles.css  # The design system - tokens + components
  templates/
    base.html            # Layout, nav, loads HTMX + the stylesheet
    index.html           # The component showcase
    dashboard.html       # The dashboard
    transactions.html    # Filters + add form + the list
    partials/            # HTML fragments returned to HTMX
      _counter.html
      _budget.html
      _transaction_row.html    # component-page demo row
      _transaction_list.html   # the filtered/paged table
      _transaction_item.html   # one read-only row
      _transaction_edit.html   # one row, inline edit form
```

## Transactions

The list is backed by `queries.search_transactions` / `count_transactions`,
which share one WHERE builder so the rows and the total always agree. Filters
live in `#tx-filters`; the add form, the pager, and Delete all `hx-include` it
so whatever comes back is filtered the same way.

Only rows the app created can be edited or deleted - `transactions.is_user_created`
is `TRUE` on insert and `FALSE` for everything `seed.py` loads. The guard is in
the SQL (`AND is_user_created`), not just the template, so a hand-made request
can't touch the source data either; those routes answer `403` and re-render the
row untouched.

The date range defaults to the newest month that has data rather than today's
month, since the dataset is historical - see `_default_range()` in `app.py`.

## The design system

Everything visual comes from `static/css/styles.css`. It opens with **design
tokens** (CSS variables for colors, spacing, radius, shadow) and includes a dark
theme via `prefers-color-scheme`. Build new UI by composing the existing classes
so the app stays consistent:

- **Layout** - `.container`, `.section`, `.grid.cols-2|3|4`, `.row`, `.card`
- **Numbers** - `.kpi` tiles (`.kpi-label` / `.kpi-value` / `.kpi-delta`)
- **Progress** - `.progress` + `.bar` (`.expense` / `.income` / `.warn` / `.over`)
- **Badges** - `.badge` (`.income` / `.expense` / `.transfer` / `.warn`)
- **Buttons** - `.btn` (`.btn-primary` / `.btn-secondary` / `.btn-ghost` / `.btn-danger`)
- **Forms** - `.field` + `.input` / `.select`
- **Tables** - `table.data`

## How the HTMX pattern works

Each interactive element issues an `hx-post`/`hx-get` to Flask; the route renders
a **partial** (a fragment from `templates/partials/`) and HTMX swaps it into the
DOM. State is passed in the form so endpoints stay stateless - the exception is
the transactions list, kept in memory so added rows persist for the session.

When wiring the real pages, replace `sample_data.py` calls in `app.py` with the
functions in [`../queries.py`](../queries.py) (e.g. `spending_by_category`,
`budget_vs_actual`, `get_recent_transactions`).
