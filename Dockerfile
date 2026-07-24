FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so the layer is cached between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The CLI (seed.py) reads the CSVs from ../data relative to src/.
COPY data/ ./data/
COPY src/ ./src/

# Everything runs from src/ (imports are top-level: db, queries, web, ...).
WORKDIR /app/src

EXPOSE 5000

# Create the tables and load the CSVs before serving. `setup` is idempotent, so
# this is a no-op on every run after the first. Compose waits for the database
# healthcheck, so Postgres is already accepting connections by this point.
CMD ["sh", "-c", "python main.py setup && exec flask --app web.app run --host 0.0.0.0 --port 5000"]
