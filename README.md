# Categorization and Analytics Dashboard

A Flask dashboard over personal transaction data, with automatic category
suggestions that learn from corrections.

## Running

Requires [Docker](https://www.docker.com/) with Docker Compose.

```bash
docker compose up -d --build
```

Then open <http://localhost:5000/>.

```bash
docker compose exec app python main.py check # Check the database connection
docker compose down                          # Shut down
docker compose down -v                       # Shut down and delete the data volume
```

Postgres is published on `localhost:5432`, so the code can also run outside Docker against the same database - see [`src/README.md`](src/README.md).
