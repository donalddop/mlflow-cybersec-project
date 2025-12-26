"""Generate embeddings for news items using Sentence Transformers."""

import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mlflow_db",
    "user": "mlflow_user",
    "password": "mlflow_password",
}

# Choose a lightweight, fast embedding model
# all-MiniLM-L6-v2: 384 dimensions, good balance of speed and quality
MODEL_NAME = "all-MiniLM-L6-v2"


def get_news_items_without_embeddings(conn, model_name: str) -> List[Tuple[int, str, str]]:
    """Fetch news items that don't have embeddings yet."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT n.id, n.title, n.content
            FROM news_items n
            LEFT JOIN embeddings e ON n.id = e.news_item_id AND e.embedding_model = %s
            WHERE e.id IS NULL
            ORDER BY n.scraped_at DESC
        """, (model_name,))
        return cur.fetchall()


def create_text_for_embedding(title: str, content: str) -> str:
    """Combine title and content for embedding."""
    # Title is usually more important, so we can weight it by repeating
    return f"{title}. {content[:500]}"  # Limit content to keep embeddings focused


def store_embeddings(conn, news_item_id: int, model_name: str, embedding: np.ndarray):
    """Store embedding in the database."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO embeddings (news_item_id, embedding_model, embedding)
            VALUES (%s, %s, %s)
            ON CONFLICT (news_item_id, embedding_model) DO UPDATE
            SET embedding = EXCLUDED.embedding
        """, (news_item_id, model_name, embedding.tolist()))
    conn.commit()


def generate_embeddings():
    """Main function to generate embeddings for all news items."""
    print(f"Loading embedding model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    print(f"✅ Model loaded (embedding dimension: {model.get_sentence_embedding_dimension()})\n")

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        # Get news items without embeddings
        items = get_news_items_without_embeddings(conn, MODEL_NAME)
        print(f"Found {len(items)} news items without embeddings\n")

        if not items:
            print("All items already have embeddings!")
            return

        # Process in batches for efficiency
        batch_size = 32
        total_processed = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_ids = [item[0] for item in batch]
            batch_texts = [create_text_for_embedding(item[1], item[2]) for item in batch]

            # Generate embeddings
            print(f"Processing batch {i//batch_size + 1}/{(len(items)-1)//batch_size + 1}...")
            embeddings = model.encode(batch_texts, show_progress_bar=False)

            # Store each embedding
            for news_id, embedding in zip(batch_ids, embeddings):
                store_embeddings(conn, news_id, MODEL_NAME, embedding)

            total_processed += len(batch)
            print(f"  Stored {total_processed}/{len(items)} embeddings")

        print(f"\n✅ Generated embeddings for {total_processed} news items")

    finally:
        conn.close()


if __name__ == "__main__":
    generate_embeddings()
