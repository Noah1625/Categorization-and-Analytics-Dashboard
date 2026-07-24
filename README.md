# Categorization and Analytics Dashboard

## Running

Requires [Docker](https://www.docker.com/) with Docker Compose. `docker-compose.yml`
defines two services: `postgres` (the database, with a persistent volume) and
`app` (the Flask web app, built from the `Dockerfile`).

### 1. Start everything

```bash
docker compose up -d --build
```

### 2. Open the app

<http://localhost:5000/>

### Other commands

```bash
docker compose exec app python main.py check # Check the database connection
docker compose down                          # Shut down the application
docker compose down -v                       # Shut down the application and remove the persistent volume
```

### Configuration

Connection settings come from environment variables and are already set for the compose network.
Postgres is also published on `localhost:5432`, so the code can run outside Docker against the same database.

See [`src/README.md`](src/README.md) for the local `venv` setup and the full variable list.
