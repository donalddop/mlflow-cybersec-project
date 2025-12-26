#!/usr/bin/env python
"""
Webhook receiver for n8n integration.
Receives article data from n8n workflows and inserts into PostgreSQL.

Usage:
    uv run python src/scripts/webhook_receiver.py

Then configure n8n to POST to: http://localhost:8001/webhook/article
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime
from config import DB_CONFIG

app = Flask(__name__)


@app.route('/webhook/article', methods=['POST'])
def receive_article():
    """Receive article from n8n webhook."""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['source', 'title', 'content', 'url']
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Parse published_at if provided, otherwise use current time
        published_at = data.get('published_at')
        if published_at:
            # Try to parse various date formats
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    published_at = datetime.strptime(published_at, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If parsing fails, use current time
                published_at = datetime.now()
        else:
            published_at = datetime.now()

        # Insert into database
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO news_items (source, title, content, url, published_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                    RETURNING id
                """, (
                    data['source'],
                    data['title'],
                    data['content'],
                    data['url'],
                    published_at
                ))

                result = cur.fetchone()
                conn.commit()

                if result:
                    return jsonify({
                        'success': True,
                        'message': 'Article inserted',
                        'article_id': result[0]
                    }), 201
                else:
                    return jsonify({
                        'success': True,
                        'message': 'Article already exists (duplicate URL)'
                    }), 200

        finally:
            conn.close()

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    print("🎣 n8n Webhook Receiver")
    print("=" * 50)
    print(f"Listening on: http://0.0.0.0:8001")
    print(f"Webhook URL: http://localhost:8001/webhook/article")
    print(f"Health check: http://localhost:8001/webhook/health")
    print("=" * 50)
    print("\nConfigure n8n to POST articles to the webhook URL")
    print("Required fields: source, title, content, url")
    print("Optional fields: published_at")
    print()

    app.run(host='0.0.0.0', port=8001, debug=True)
