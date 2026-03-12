"""
Create USPTO database and schema.
"""

import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import os
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("USPTO_DB_NAME", "uspto_data")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def main():
    schema_path = Path(__file__).resolve().parent.parent / "uspto" / "database" / "uspto_schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database="postgres",
            user=DB_USER, password=DB_PASSWORD,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"Created database '{DB_NAME}'.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(schema_sql)
    cur.close()
    conn.close()
    print("USPTO schema created successfully.")


if __name__ == "__main__":
    main()
