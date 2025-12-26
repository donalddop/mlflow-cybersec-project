"""
Flask web application for labeling cybersecurity news articles.

Provides a card-based UI where users can swipe through articles and mark them
as relevant or not relevant.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, render_template, request, jsonify, make_response
import psycopg2
import uuid
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'


def get_or_create_user_id():
    """Get or create a user ID from cookie."""
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id


def get_db_connection():
    """Create a database connection."""
    return psycopg2.connect(**DB_CONFIG)


@app.route('/')
def index():
    """Render the homepage with recent articles."""
    user_id = get_or_create_user_id()
    resp = make_response(render_template('home.html'))
    resp.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1 year
    return resp


@app.route('/label')
def label_page():
    """Render the labeling interface."""
    return render_template('label.html')


@app.route('/api/recent_articles')
def get_recent_articles():
    """Get recent articles from the last week with voting stats."""
    days = request.args.get('days', 7, type=int)
    user_id = get_or_create_user_id()

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    n.id,
                    n.source,
                    n.title,
                    n.content,
                    n.url,
                    n.published_at,
                    COUNT(CASE WHEN f.label = 'relevant' THEN 1 END) as upvotes,
                    COUNT(CASE WHEN f.label = 'not_relevant' THEN 1 END) as downvotes,
                    MAX(CASE WHEN f.user_id = %s THEN f.label END) as user_vote
                FROM news_items n
                LEFT JOIN feedback f ON n.id = f.news_item_id
                WHERE n.published_at > NOW() - INTERVAL '%s days'
                GROUP BY n.id, n.source, n.title, n.content, n.url, n.published_at
                ORDER BY n.published_at DESC
                LIMIT 100
            """, (user_id, days))
            rows = cur.fetchall()

            articles = []
            for row in rows:
                articles.append({
                    'id': row[0],
                    'source': row[1],
                    'title': row[2],
                    'content': row[3],
                    'url': row[4],
                    'published_at': row[5].isoformat() if row[5] else None,
                    'upvotes': row[6],
                    'downvotes': row[7],
                    'user_vote': row[8],
                })

            return jsonify({'articles': articles})
    finally:
        conn.close()


@app.route('/api/stats')
def get_stats():
    """Get labeling statistics."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Total counts
            cur.execute("SELECT COUNT(*) FROM news_items")
            total_items = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM feedback")
            total_labeled = cur.fetchone()[0]

            # Label breakdown
            cur.execute("""
                SELECT label, COUNT(*) as count
                FROM feedback
                GROUP BY label
            """)
            label_counts = dict(cur.fetchall())

            return jsonify({
                'total_items': total_items,
                'total_labeled': total_labeled,
                'remaining': total_items - total_labeled,
                'relevant': label_counts.get('relevant', 0),
                'not_relevant': label_counts.get('not_relevant', 0),
            })
    finally:
        conn.close()


@app.route('/api/next_article')
def get_next_article():
    """Get the next unlabeled article."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT n.id, n.source, n.title, n.content, n.url, n.published_at
                FROM news_items n
                LEFT JOIN feedback f ON n.id = f.news_item_id
                WHERE f.id IS NULL
                ORDER BY n.published_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()

            if not row:
                return jsonify({'article': None})

            article = {
                'id': row[0],
                'source': row[1],
                'title': row[2],
                'content': row[3],
                'url': row[4],
                'published_at': row[5].isoformat() if row[5] else None,
            }

            return jsonify({'article': article})
    finally:
        conn.close()


@app.route('/api/label', methods=['POST'])
def submit_label():
    """Submit or update a label for an article (multi-user voting)."""
    data = request.json
    article_id = data.get('article_id')
    label = data.get('label')
    user_id = get_or_create_user_id()

    if not article_id or label not in ['relevant', 'not_relevant']:
        return jsonify({'error': 'Invalid request'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if user already voted
            cur.execute("""
                SELECT id FROM feedback
                WHERE news_item_id = %s AND user_id = %s
            """, (article_id, user_id))
            existing = cur.fetchone()

            if existing:
                # Update existing vote
                cur.execute("""
                    UPDATE feedback
                    SET label = %s, created_at = CURRENT_TIMESTAMP
                    WHERE news_item_id = %s AND user_id = %s
                """, (label, article_id, user_id))
            else:
                # Insert new vote
                cur.execute("""
                    INSERT INTO feedback (news_item_id, label, user_id)
                    VALUES (%s, %s, %s)
                """, (article_id, label, user_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    from config import WEB_HOST, WEB_PORT, WEB_DEBUG
    app.run(debug=WEB_DEBUG, host=WEB_HOST, port=WEB_PORT)
