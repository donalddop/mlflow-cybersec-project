# Quick Setup Guide

## First Time Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd mlflow-project

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 3. Start infrastructure
docker-compose -f config/docker-compose.yml up -d

# 4. Install dependencies
uv sync

# 5. Initialize database
uv run python run.py init-db

# 6. Ingest some news articles
uv run python run.py ingest

# 7. Generate embeddings
uv run python run.py embed

# 8. Start labeling articles
uv run python run.py web
# Open http://localhost:8000 in your browser

# 9. After labeling 20-30 articles, train the model
uv run python run.py train

# 10. View results in MLflow
# Open http://localhost:5000 in your browser
```

## Daily Usage

```bash
# Fetch new articles
uv run python run.py ingest

# Generate embeddings for new articles
uv run python run.py embed

# Label articles via web UI
uv run python run.py web

# Check progress
uv run python run.py status

# Retrain model when you have new labels
uv run python run.py train
```

## Available Commands

Run `uv run python run.py help` to see all available commands:

- `web` - Launch web labeling interface
- `ingest` - Fetch news from RSS feeds
- `embed` - Generate embeddings
- `label` - CLI labeling tool
- `train` - Train the model
- `status` - Show database statistics
- `init-db` - Initialize database
- `pipeline` - Run ingest + embed

## Infrastructure

### Start/Stop Docker Services

```bash
# Start
docker-compose -f config/docker-compose.yml up -d

# Stop
docker-compose -f config/docker-compose.yml down

# View logs
docker-compose -f config/docker-compose.yml logs -f
```

### Access Services

- **Web UI**: http://localhost:8000
- **MLflow**: http://localhost:5000
- **PostgreSQL**: localhost:5432

## Configuration

Edit [config/config.py](config/config.py) to customize:
- Database connection
- MLflow settings
- RSS feed sources
- Model parameters
- Web server settings

## Troubleshooting

### Docker containers not starting
```bash
docker-compose -f config/docker-compose.yml down
docker-compose -f config/docker-compose.yml up -d
```

### Database connection errors
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection
psql -h localhost -p 5432 -U mlflow_user -d mlflow_db
```

### Web app not loading
```bash
# Kill any running processes on port 8000
lsof -ti:8000 | xargs kill -9

# Restart the web app
uv run python run.py web
```

### Import errors
```bash
# Reinstall dependencies
rm -rf .venv
uv sync
```

## Next Steps

1. **Integrate n8n**: See [docs/n8n-integration.md](docs/n8n-integration.md)
2. **Customize RSS feeds**: Edit `RSS_FEEDS` in [config/config.py](config/config.py)
3. **Improve the model**: Label more articles and retrain
4. **Deploy to production**: Use Docker Compose in your cloud environment
