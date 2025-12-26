# Migrating n8n from Internal Tables to PostgreSQL

This guide helps you migrate your n8n workflow from using internal SQLite data tables to PostgreSQL.

## Why Migrate?

**Current Setup (Internal Tables):**
- Data stored in n8n's internal SQLite database
- Isolated from other systems
- Limited to n8n's data table features

**After Migration (PostgreSQL):**
- Shared database with MLflow project
- Articles automatically available in web UI
- Direct integration with ML pipeline
- More powerful query capabilities

---

## Quick Start (5 Minutes)

### Step 1: Add PostgreSQL Node to Your n8n Workflow

1. Open your existing n8n workflow
2. Find where you currently save to "n8n Tables"
3. Replace that node with a **PostgreSQL** node

### Step 2: Create Database Credentials

In the PostgreSQL node:

1. Click **"Credential to connect with"** → **"Create New"**
2. Fill in these details:

```
Host: localhost
Database: mlflow_db
User: mlflow_user
Password: mlflow_password
Port: 5432
SSL Mode: disable (for local dev)
```

💡 If your n8n is running in Docker, use your machine's IP instead of `localhost`

### Step 3: Configure the Insert

**Operation:** Insert

**Table:** `news_items`

**Columns to Match:** (Check all)
- source
- title
- content
- url
- published_at

**Mode:** Insert - Multiple Rows

**Options:**
- ✅ Skip On Conflict (recommended - prevents duplicates)

### Step 4: Map Your Data

Make sure your workflow provides these fields before the PostgreSQL node:

| Field | Example Value | Required |
|-------|--------------|----------|
| `source` | "BleepingComputer" | ✅ Yes |
| `title` | "New Ransomware Campaign..." | ✅ Yes |
| `content` | "Article text here..." | ✅ Yes |
| `url` | "https://..." | ✅ Yes |
| `published_at` | "2025-12-26T15:30:00" | Optional |

---

## Example: Migrating an RSS Feed Workflow

### Before (Using n8n Tables)

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  RSS Feed   │───▶│  Transform   │───▶│  n8n Table   │
│   Reader    │    │     Data     │    │    Insert    │
└─────────────┘    └──────────────┘    └──────────────┘
```

### After (Using PostgreSQL)

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  RSS Feed   │───▶│  Transform   │───▶│  PostgreSQL  │
│   Reader    │    │     Data     │    │    Insert    │
└─────────────┘    └──────────────┘    └──────────────┘
```

### Data Transformation Code

Add a **Code** node before PostgreSQL to format the data correctly:

```javascript
// Transform RSS feed data for PostgreSQL
const items = [];

for (const item of $input.all()) {
  items.push({
    json: {
      source: 'BleepingComputer',  // Change this for each feed
      title: item.json.title || '',
      content: item.json.content || item.json.description || '',
      url: item.json.link || '',
      published_at: item.json.pubDate || new Date().toISOString()
    }
  });
}

return items;
```

---

## Testing the Integration

### 1. Run Your Workflow

Click **"Execute Workflow"** in n8n

### 2. Check the Database

```bash
# Connect to database
psql -h localhost -U mlflow_user -d mlflow_db

# Check if articles were inserted
SELECT id, source, title FROM news_items ORDER BY id DESC LIMIT 5;

# Count articles by source
SELECT source, COUNT(*) FROM news_items GROUP BY source;
```

### 3. Verify in Web UI

```bash
# Start the web interface
make web

# Open http://localhost:8000
# Your n8n articles should appear!
```

---

## Handling Different n8n Data Sources

### If You Have Multiple RSS Feeds

Option 1: Separate workflows for each source
```javascript
// Set source in Code node
{ source: 'BleepingComputer', ... }
```

Option 2: Use n8n's IF node to determine source from URL
```javascript
// Detect source from URL
const url = item.json.link || '';
let source = 'Unknown';

if (url.includes('bleepingcomputer.com')) {
  source = 'BleepingComputer';
} else if (url.includes('thehackernews.com')) {
  source = 'TheHackerNews';
} else if (url.includes('darkreading.com')) {
  source = 'DarkReading';
}

return { json: { ...item.json, source } };
```

### If You're Scraping Custom Sources

```javascript
// Custom web scraper example
{
  source: 'Company Security Blog',
  title: item.json.headline,
  content: item.json.body_text,
  url: item.json.permalink,
  published_at: item.json.post_date
}
```

---

## Migrating Existing Data

If you have articles in n8n's internal tables that you want to migrate:

### Step 1: Export from n8n Tables

1. Add a **Read/Write Files from Disk** node
2. Set Mode: Write
3. Format: JSON
4. File Path: `/tmp/n8n_export.json`

### Step 2: Import to PostgreSQL

Create a Python script:

```python
# migrate_n8n_data.py
import json
import psycopg2
from config import DB_CONFIG

# Load exported data
with open('/tmp/n8n_export.json') as f:
    data = json.load(f)

conn = psycopg2.connect(**DB_CONFIG)
try:
    with conn.cursor() as cur:
        for item in data:
            cur.execute("""
                INSERT INTO news_items (source, title, content, url, published_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
            """, (
                item.get('source', 'n8n'),
                item.get('title'),
                item.get('content'),
                item.get('url'),
                item.get('published_at')
            ))
    conn.commit()
    print(f"✅ Migrated {len(data)} articles")
finally:
    conn.close()
```

Run it:
```bash
uv run python migrate_n8n_data.py
```

---

## Troubleshooting

### Error: "Connection refused"

**Problem:** n8n can't reach PostgreSQL

**Solutions:**
1. If n8n is in Docker, use your machine's IP instead of `localhost`:
   ```bash
   # Find your IP
   ip addr show | grep inet

   # Or on Mac:
   ipconfig getifaddr en0
   ```

2. Make sure PostgreSQL is running:
   ```bash
   docker compose -f config/docker-compose.yml ps
   ```

3. Check firewall allows port 5432

### Error: "Duplicate key value violates unique constraint"

**Problem:** Trying to insert the same article twice (same URL)

**Solution:** Enable "Skip On Conflict" in PostgreSQL node options

### Error: "Null value in column 'content' violates not-null constraint"

**Problem:** Missing required fields

**Solution:** Add default values in your transformation:
```javascript
content: item.json.content || item.json.description || 'No content available'
```

### Articles Not Appearing in Web UI

**Possible causes:**

1. **Wrong date range**: Web UI shows articles from last 7 days by default
   ```bash
   # Check recent articles
   SELECT COUNT(*) FROM news_items
   WHERE published_at > NOW() - INTERVAL '7 days';
   ```

2. **published_at is in the future**: Verify timestamps
   ```javascript
   // Always use current time if pubDate is invalid
   published_at: item.json.pubDate || new Date().toISOString()
   ```

3. **Web UI not refreshed**: Hard refresh browser (Ctrl+Shift+R)

---

## Next Steps After Migration

1. ✅ **Generate Embeddings**
   ```bash
   make embed
   ```

2. ✅ **Start Labeling**
   ```bash
   make web
   # Visit http://localhost:8000 and start voting
   ```

3. ✅ **Train Your First Model**
   ```bash
   # After labeling ~50 articles
   make train
   ```

4. ✅ **Automate Everything** (See docs/n8n-integration.md)
   - Scheduled ingestion
   - Automated embedding generation
   - Weekly model retraining

---

## Advanced: Using the Webhook Receiver

For more flexibility and features, use the webhook receiver instead of direct PostgreSQL:

### Start Webhook Receiver

```bash
uv run python src/scripts/webhook_receiver.py
```

### Configure n8n HTTP Request Node

**Method:** POST
**URL:** `http://localhost:8001/webhook/article`
**Body:**

```json
{
  "source": "{{ $json.source }}",
  "title": "{{ $json.title }}",
  "content": "{{ $json.content }}",
  "url": "{{ $json.url }}",
  "published_at": "{{ $json.published_at }}"
}
```

**Benefits:**
- Better error handling
- Request logging
- Easy to add authentication
- Can add custom validation
- Decoupled from database

See [n8n-integration.md](n8n-integration.md) for full details.

---

## Getting Help

- 📖 [Full n8n Integration Guide](n8n-integration.md)
- 🚀 [Quick Start Guide](../QUICKSTART.md)
- 📚 [Main README](../README.md)

Happy automating! 🤖
