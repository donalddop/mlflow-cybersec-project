# n8n Integration Guide

This guide explains how to integrate your n8n cybersecurity news gathering workflow with the ML triage system.

## Overview

Your n8n workflow should:
1. Gather cybersecurity news from various sources
2. Insert articles into the PostgreSQL database
3. Optionally trigger embedding generation
4. Optionally trigger model inference for new articles

## Database Connection

Configure n8n to connect to the PostgreSQL database:

```
Host: localhost (or your server IP)
Port: 5432
Database: mlflow_db
User: mlflow_user
Password: mlflow_password
```

## Method 1: Direct PostgreSQL Insert

### Setup

1. In n8n, add a **Postgres** node after your news scraping nodes
2. Configure the connection using the credentials above
3. Set operation to **Insert**
4. Select table: `news_items`

### Data Mapping

Map your workflow data to the database schema:

| Database Column | n8n Expression | Description |
|----------------|----------------|-------------|
| `source` | `{{ $json.source }}` | News source name (e.g., "BleepingComputer") |
| `title` | `{{ $json.title }}` | Article title |
| `url` | `{{ $json.url }}` | Full article URL (must be unique) |
| `content` | `{{ $json.content }}` | Article content/summary |
| `published_at` | `{{ $json.published_at }}` | Publication timestamp |
| `metadata` | `{{ $json }}` | (Optional) Store full JSON as JSONB |

### Example n8n Workflow

```json
{
  "nodes": [
    {
      "name": "RSS Feed",
      "type": "n8n-nodes-base.rssFeedRead",
      "parameters": {
        "url": "https://www.bleepingcomputer.com/feed/"
      }
    },
    {
      "name": "Format Data",
      "type": "n8n-nodes-base.set",
      "parameters": {
        "values": {
          "string": [
            {
              "name": "source",
              "value": "BleepingComputer"
            },
            {
              "name": "title",
              "value": "={{ $json.title }}"
            },
            {
              "name": "url",
              "value": "={{ $json.link }}"
            },
            {
              "name": "content",
              "value": "={{ $json.content }}"
            },
            {
              "name": "published_at",
              "value": "={{ $json.pubDate }}"
            }
          ]
        }
      }
    },
    {
      "name": "Insert to PostgreSQL",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "insert",
        "table": "news_items",
        "columns": "source, title, url, content, published_at",
        "onConflict": "Do Nothing"
      }
    }
  ]
}
```

## Method 2: HTTP API Endpoint (Future)

For more flexibility, you can create a Flask API endpoint to receive articles from n8n.

### Create API endpoint (app.py)

```python
@app.route('/api/ingest', methods=['POST'])
def ingest_article():
    """Receive articles from n8n webhook."""
    data = request.json

    required_fields = ['source', 'title', 'url']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO news_items (source, title, url, content, published_at, metadata)
                VALUES (%(source)s, %(title)s, %(url)s, %(content)s, %(published_at)s, %(metadata)s)
                ON CONFLICT (url) DO NOTHING
                RETURNING id
            """, {
                'source': data['source'],
                'title': data['title'],
                'url': data['url'],
                'content': data.get('content', ''),
                'published_at': data.get('published_at'),
                'metadata': json.dumps(data)
            })
            result = cur.fetchone()
        conn.commit()

        if result:
            return jsonify({'success': True, 'id': result[0]}), 201
        else:
            return jsonify({'success': False, 'message': 'Duplicate article'}), 200

    finally:
        conn.close()
```

### n8n Webhook Node

1. Add a **Webhook** node to receive the trigger
2. Add an **HTTP Request** node to POST to your endpoint:

```
Method: POST
URL: http://your-server:8000/api/ingest
Body Content Type: JSON
Body:
{
  "source": "{{ $json.source }}",
  "title": "{{ $json.title }}",
  "url": "{{ $json.link }}",
  "content": "{{ $json.content }}",
  "published_at": "{{ $json.pubDate }}"
}
```

## Automated Pipeline Triggers

### Option 1: Scheduled Workflows

Set up n8n schedules to:
1. Insert news every hour
2. Trigger embedding generation after insert (run `generate_embeddings.py`)
3. Trigger model retraining weekly

### Option 2: Execute Command Node

After inserting articles, use n8n's **Execute Command** node to run:

```bash
# Generate embeddings for new articles
cd /path/to/mlflow-project && uv run generate_embeddings.py

# Run inference on unlabeled articles
cd /path/to/mlflow-project && uv run predict.py

# Retrain model if enough new labels
cd /path/to/mlflow-project && uv run train.py
```

## Conflict Handling

The database schema uses `url` as a unique constraint to prevent duplicates:

```sql
CREATE TABLE news_items (
    url TEXT UNIQUE NOT NULL,
    ...
)
```

When inserting, use `ON CONFLICT (url) DO NOTHING` to skip duplicates gracefully.

## Best Practices

1. **Batch Insertions**: Insert multiple articles in a single transaction
2. **Error Handling**: Catch and log insertion errors in n8n
3. **Deduplication**: Check for existing URLs before processing
4. **Monitoring**: Track insertion rates and failures
5. **Scheduled Generation**: Run embedding generation on a schedule, not after each insert

## Monitoring n8n Integration

Add these queries to monitor your integration:

```sql
-- Articles ingested in the last 24 hours
SELECT source, COUNT(*) as count
FROM news_items
WHERE scraped_at > NOW() - INTERVAL '24 hours'
GROUP BY source;

-- Articles awaiting embeddings
SELECT COUNT(*) FROM news_items n
LEFT JOIN embeddings e ON n.id = e.news_item_id
WHERE e.id IS NULL;

-- Recent labeling activity
SELECT DATE(created_at) as date, label, COUNT(*) as count
FROM feedback
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), label
ORDER BY date DESC;
```

## Troubleshooting

**Connection refused**: Ensure PostgreSQL port 5432 is accessible to n8n

**Duplicate key errors**: Verify you're using `ON CONFLICT DO NOTHING`

**Missing data**: Check that all required fields are populated

**Timestamp issues**: Ensure timestamps are in ISO 8601 format

## Next Steps

After setting up n8n integration:

1. Verify articles are appearing in the database
2. Run embedding generation
3. Use the web UI to label articles
4. Train your first model
5. Set up automated retraining
