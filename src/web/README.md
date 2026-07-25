# Web (Flask + HTMX)

The Flask app: a Dashboard page and a Transactions page, both backed by
`queries.py`. Routes render either a full page or a partial that HTMX swaps
into the DOM.

## Run

From the `src/` directory:

```bash
flask --app web.app run --debug
```

Then open <http://127.0.0.1:5000/>.

## Layout

```
web/
  app.py                 # Routes: pages + HTMX fragment endpoints
  static/css/styles.css  # Design tokens + component classes
  templates/
    base.html            # Layout and nav
    dashboard.html       # KPIs, charts, filters
    transactions.html    # Filters + add form + list
    partials/            # Fragments returned to HTMX
```
