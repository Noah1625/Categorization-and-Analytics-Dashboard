import os
import psycopg2
from psycopg2.extensions import connection
from dotenv import load_dotenv

# Load a .env file if present
load_dotenv()

def get_config() -> dict[str, str]:
    """Return connection parameters, defaulting to the docker-compose service."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "user": os.getenv("POSTGRES_USER", "dashboard"),
        "password": os.getenv("POSTGRES_PASSWORD", "dashboard"),
        "dbname": os.getenv("POSTGRES_DB", "analytics"),
    }


def get_connection() -> connection:
    """Open a new connection to PostgreSQL using the environment config."""
    cfg = get_config()
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        dbname=cfg["dbname"],
    )
