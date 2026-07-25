# Running locally

Running outside Docker, against the Postgres container. Requires Python 3.11+.

## Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Read from environment variables, with defaults that match `docker-compose.yml`,
so it runs with no setup. To override, copy `.env.example` to `.env` in the repo
root.

| Variable            | Default     |
|---------------------|-------------|
| `POSTGRES_HOST`     | `localhost` |
| `POSTGRES_PORT`     | `5432`      |
| `POSTGRES_USER`     | `dashboard` |
| `POSTGRES_PASSWORD` | `dashboard` |
| `POSTGRES_DB`       | `analytics` |

## Commands

Start the database from the repo root with `docker compose up -d`, then from
`src/`:

```bash
python main.py check # verify the connection
python main.py setup # create tables if missing, then load the CSV data (idempotent)
python main.py demo  # run the example read queries and print results
```

See [`web/README.md`](web/README.md) to run the Flask app.
