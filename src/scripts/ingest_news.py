"""
Ingest cybersecurity news from RSS feeds.

This script scrapes cybersecurity news from various sources and stores them in the database.
"""

import psycopg2
import feedparser
from datetime import datetime
from typing import List, Dict
import time

# Database connection parameters
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mlflow_db",
    "user": "mlflow_user",
    "password": "mlflow_password",
}

# Cybersecurity news RSS feeds
RSS_FEEDS = {
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "TheHackerNews": "https://feeds.feedburner.com/TheHackersNews",
    "SecurityWeek": "https://www.securityweek.com/feed/",
    "KrebsOnSecurity": "https://krebsonsecurity.com/feed/",
    "DarkReading": "https://www.darkreading.com/rss.xml",
}


def parse_published_date(entry) -> datetime:
    """Parse the published date from a feed entry."""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.now()


def fetch_feed(source: str, url: str) -> List[Dict]:
    """Fetch and parse a single RSS feed."""
    print(f"Fetching {source}...")

    try:
        feed = feedparser.parse(url)
        items = []

        for entry in feed.entries:
            item = {
                'source': source,
                'title': entry.get('title', ''),
                'url': entry.get('link', ''),
                'content': entry.get('summary', '') or entry.get('description', ''),
                'published_at': parse_published_date(entry),
            }
            items.append(item)

        print(f"  Found {len(items)} items from {source}")
        return items

    except Exception as e:
        print(f"  Error fetching {source}: {e}")
        return []


def insert_news_items(conn, items: List[Dict]) -> int:
    """Insert news items into the database, skipping duplicates."""
    inserted = 0

    with conn.cursor() as cur:
        for item in items:
            try:
                cur.execute("""
                    INSERT INTO news_items (source, title, url, content, published_at)
                    VALUES (%(source)s, %(title)s, %(url)s, %(content)s, %(published_at)s)
                    ON CONFLICT (url) DO NOTHING
                    RETURNING id
                """, item)

                if cur.fetchone():
                    inserted += 1

            except Exception as e:
                print(f"  Error inserting item: {e}")
                conn.rollback()
                continue

        conn.commit()

    return inserted


def ingest_all_feeds():
    """Main function to ingest news from all RSS feeds."""
    print("Starting news ingestion...\n")

    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        total_fetched = 0
        total_inserted = 0

        for source, url in RSS_FEEDS.items():
            items = fetch_feed(source, url)
            total_fetched += len(items)

            if items:
                inserted = insert_news_items(conn, items)
                total_inserted += inserted
                print(f"  Inserted {inserted} new items\n")

            # Be polite to servers
            time.sleep(1)

        print(f"\n✅ Ingestion complete!")
        print(f"Total items fetched: {total_fetched}")
        print(f"New items inserted: {total_inserted}")
        print(f"Duplicates skipped: {total_fetched - total_inserted}")

    finally:
        conn.close()


if __name__ == "__main__":
    ingest_all_feeds()
