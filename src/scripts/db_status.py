"""Check database status and show statistics."""

import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mlflow_db",
    "user": "mlflow_user",
    "password": "mlflow_password",
}


def show_status():
    """Display database statistics."""
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            print("=" * 60)
            print("DATABASE STATUS")
            print("=" * 60)

            # Check if tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('news_items', 'embeddings', 'predictions', 'feedback')
                ORDER BY table_name;
            """)
            tables = cur.fetchall()

            if not tables:
                print("\n❌ Schema not initialized. Run: uv run init_db.py\n")
                return

            print(f"\n✅ Schema initialized ({len(tables)} tables found)\n")

            # Count records in each table
            for table_name in ['news_items', 'embeddings', 'predictions', 'feedback']:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                print(f"  {table_name:20s}: {count:6d} records")

            # Show recent news items
            cur.execute("""
                SELECT source, COUNT(*) as count
                FROM news_items
                GROUP BY source
                ORDER BY count DESC
            """)
            sources = cur.fetchall()

            if sources:
                print("\n" + "-" * 60)
                print("NEWS ITEMS BY SOURCE")
                print("-" * 60)
                for source, count in sources:
                    print(f"  {source:30s}: {count:6d} items")

            # Show latest items
            cur.execute("""
                SELECT title, source, published_at
                FROM news_items
                ORDER BY scraped_at DESC
                LIMIT 5
            """)
            latest = cur.fetchall()

            if latest:
                print("\n" + "-" * 60)
                print("LATEST NEWS ITEMS")
                print("-" * 60)
                for title, source, pub_date in latest:
                    title_preview = title[:50] + "..." if len(title) > 50 else title
                    print(f"  [{source}] {title_preview}")

            print("\n" + "=" * 60 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    show_status()
