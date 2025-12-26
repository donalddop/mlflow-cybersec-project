"""Interactive CLI tool for labeling news articles as relevant or not relevant."""

import psycopg2
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mlflow_db",
    "user": "mlflow_user",
    "password": "mlflow_password",
}


def get_unlabeled_items(conn, limit=50):
    """Fetch news items that haven't been labeled yet."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT n.id, n.source, n.title, n.content, n.published_at
            FROM news_items n
            LEFT JOIN feedback f ON n.id = f.news_item_id
            WHERE f.id IS NULL
            ORDER BY n.published_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def save_feedback(conn, news_item_id: int, label: str, notes: str = None):
    """Save feedback label to database."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO feedback (news_item_id, label, notes)
            VALUES (%s, %s, %s)
        """, (news_item_id, label, notes))
    conn.commit()


def get_feedback_stats(conn):
    """Get current labeling statistics."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT label, COUNT(*) as count
            FROM feedback
            GROUP BY label
        """)
        return dict(cur.fetchall())


def display_article(idx, total, source, title, content, published_at):
    """Display article for labeling."""
    print("\n" + "=" * 80)
    print(f"Article {idx}/{total}")
    print("=" * 80)
    print(f"Source: {source}")
    print(f"Published: {published_at}")
    print(f"\nTitle: {title}")
    print(f"\nContent Preview:")
    print(content[:400] + "..." if len(content) > 400 else content)
    print("=" * 80)


def label_articles():
    """Main interactive labeling loop."""
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        # Get current stats
        stats = get_feedback_stats(conn)
        total_labeled = sum(stats.values())
        print("\n" + "=" * 80)
        print("CYBERSECURITY NEWS LABELING TOOL")
        print("=" * 80)
        print(f"\nCurrent labels: {total_labeled} total")
        for label, count in stats.items():
            print(f"  - {label}: {count}")
        print()

        # Get unlabeled items
        items = get_unlabeled_items(conn)

        if not items:
            print("✅ All articles have been labeled!")
            return

        print(f"Found {len(items)} unlabeled articles\n")
        print("Commands:")
        print("  r  = RELEVANT (this article is worth your attention)")
        print("  n  = NOT RELEVANT (this article can be ignored)")
        print("  s  = SKIP (decide later)")
        print("  q  = QUIT (exit and save progress)")
        print("\nGoal: Label articles based on whether YOU would want to see them in your feed")
        print()

        labeled_count = 0

        for i, (news_id, source, title, content, published_at) in enumerate(items, 1):
            display_article(i, len(items), source, title, content, published_at)

            while True:
                choice = input("\nYour choice (r=relevant / n=not relevant / s=skip / q=quit): ").strip().lower()

                if choice == 'q':
                    print(f"\n✅ Labeled {labeled_count} articles this session")
                    return
                elif choice == 's':
                    print("⊘ Skipped")
                    break
                elif choice == 'r':
                    save_feedback(conn, news_id, 'relevant')
                    labeled_count += 1
                    print("✓ Marked as RELEVANT (worth reading)")
                    break
                elif choice == 'n':
                    save_feedback(conn, news_id, 'not_relevant')
                    labeled_count += 1
                    print("✓ Marked as NOT RELEVANT (can ignore)")
                    break
                else:
                    print("❌ Invalid choice. Please enter: r (relevant), n (not relevant), s (skip), or q (quit)")

        print(f"\n✅ Finished! Labeled {labeled_count} articles this session")

        # Show final stats
        stats = get_feedback_stats(conn)
        print("\nFinal statistics:")
        for label, count in stats.items():
            print(f"  - {label}: {count}")

    finally:
        conn.close()


if __name__ == "__main__":
    label_articles()
