# Web (Flask + HTMX)

A small Flask app that serves the shared **component / style guide** page and a
few live HTMX demos. It runs on its own with in-memory sample data — no database
required — so it's a safe sandbox for agreeing on the look and feel before the
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
  app.py                 # Flask routes: the page + HTMX fragment endpoints
  sample_data.py         # In-memory demo data (swap for queries.py later)
  static/css/styles.css  # The design system — tokens + components
  templates/
    base.html            # Layout, nav, loads HTMX + the stylesheet
    index.html           # The component showcase
    partials/            # HTML fragments returned to HTMX
      _counter.html
      _budget.html
      _transaction_row.html
```

## The design system

Everything visual comes from `static/css/styles.css`. It opens with **design
tokens** (CSS variables for colors, spacing, radius, shadow) and includes a dark
theme via `prefers-color-scheme`. Build new UI by composing the existing classes
so the app stays consistent:

- **Layout** — `.container`, `.section`, `.grid.cols-2|3|4`, `.row`, `.card`
- **Numbers** — `.kpi` tiles (`.kpi-label` / `.kpi-value` / `.kpi-delta`)
- **Progress** — `.progress` + `.bar` (`.expense` / `.income` / `.warn` / `.over`)
- **Badges** — `.badge` (`.income` / `.expense` / `.transfer` / `.warn`)
- **Buttons** — `.btn` (`.btn-primary` / `.btn-secondary` / `.btn-ghost` / `.btn-danger`)
- **Forms** — `.field` + `.input` / `.select`
- **Tables** — `table.data`

## How the HTMX pattern works

Each interactive element issues an `hx-post`/`hx-get` to Flask; the route renders
a **partial** (a fragment from `templates/partials/`) and HTMX swaps it into the
DOM. State is passed in the form so endpoints stay stateless — the exception is
the transactions list, kept in memory so added rows persist for the session.

When wiring the real pages, replace `sample_data.py` calls in `app.py` with the
functions in [`../queries.py`](../queries.py) (e.g. `spending_by_category`,
`budget_vs_actual`, `get_recent_transactions`).
