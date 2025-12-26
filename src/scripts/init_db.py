"""Initialize the database schema for the cybersecurity signal triage system."""

import psycopg2
from pathlib import Path

# Database connection parameters
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mlflow_db",
    "user": "mlflow_user",
    "password": "mlflow_password",
}


def init_database():
    """Apply the schema.sql file to initialize the database."""

    # Read the schema file
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    # Connect to the database
    print("Connecting to PostgreSQL database...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            print("Executing schema SQL...")
            cur.execute(schema_sql)
            print("✅ Database schema initialized successfully!")

            # Verify tables were created
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            print(f"\nCreated tables:")
            for table in tables:
                print(f"  - {table[0]}")

    finally:
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    init_database()
