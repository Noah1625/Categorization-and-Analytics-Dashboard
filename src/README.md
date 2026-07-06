# Python Dev

Loads the processed CSV data into a PostgreSQL database using a Python client.
The database runs in Docker, and a small CLI connects, creates the tables (once),
and loads the data.

## Requirements

- [Docker](https://www.docker.com/) (with Docker Compose)
- Python 3.11+

## Setting Up Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Connection settings are read from environment variables, with defaults that match `docker-compose.yml`, so it runs with no setup. To override, copy `.env.example` to `.env` (in the repo root) and edit it.

| Variable            | Default     |
|---------------------|-------------|
| `POSTGRES_HOST`     | `localhost` |
| `POSTGRES_PORT`     | `5432`      |
| `POSTGRES_USER`     | `dashboard` |
| `POSTGRES_PASSWORD` | `dashboard` |
| `POSTGRES_DB`       | `analytics` |

## Running

### 1. Start the database

From the repo root:

```bash
docker compose up -d
```

This starts a `postgres:16` container named `analytics_postgres` with the
credentials above and a persistent volume.

### 2. Load the database

From the `src/` directory:

```bash
python main.py check # verify the connection (prints server version)
python main.py setup # create tables if missing, then load the CSV data
python main.py demo  # run the example read queries and print results
```

> INFO: `setup` is idempotent.

### 3. Stop / reset the database

```bash
docker compose down    # stop the container (keeps data volume)
docker compose down -v # stop and delete the data volume
```