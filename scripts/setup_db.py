"""
Create the Twitter database and schema.
Run: python scripts/setup_db.py
Requires PostgreSQL running locally.
"""

import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from config import Config


def main():
    cfg = Config()
    schema_path = Path(__file__).resolve().parent.parent / "database" / "twitter_schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    # Connect to postgres to create DB if needed
    try:
        conn = psycopg2.connect(
            host=cfg.DB_HOST,
            port=cfg.DB_PORT,
            database="postgres",
            user=cfg.DB_USER,
            password=cfg.DB_PASSWORD,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (cfg.DB_NAME,),
        )
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{cfg.DB_NAME}"')
            print(f"Created database '{cfg.DB_NAME}'.")
        cur.close()
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"Cannot connect to PostgreSQL: {e}")
        print("Ensure PostgreSQL is running and credentials in .env are correct.")
        sys.exit(1)

    # Connect to target DB and apply schema
    conn = psycopg2.connect(
        host=cfg.DB_HOST,
        port=cfg.DB_PORT,
        database=cfg.DB_NAME,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        cur.execute(schema_sql)
        print("Schema created successfully.")
    except Exception as e:
        print(f"Error applying schema: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
