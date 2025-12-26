# Quick Start Guide

Get the Cybersecurity Signal Triage Platform running in 5 minutes.

## Prerequisites

Install these before proceeding:

1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
2. **Python 3.10+** - [Download here](https://www.python.org/downloads/)
3. **uv** - Install with:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## Installation

### Option 1: One-Command Setup (Recommended)

```bash
git clone <your-repo-url>
cd mlflow-project
make setup
```

This will:
- ✅ Install Python dependencies
- ✅ Start PostgreSQL and MLflow in Docker
- ✅ Initialize the database schema

### Option 2: Manual Setup

```bash
# 1. Clone repository
git clone <your-repo-url>
cd mlflow-project

# 2. Install dependencies
uv sync

# 3. Start infrastructure
docker compose -f config/docker-compose.yml up -d

# 4. Initialize database
uv run python src/scripts/init_db.py
```

## First Run

### 1. Ingest News Articles

```bash
make ingest
```

This fetches articles from 5 cybersecurity news sources:
- BleepingComputer
- The Hacker News
- Dark Reading
- Krebs on Security
- Security Week

### 2. Generate Embeddings

```bash
make embed
```

Creates semantic embeddings for all articles using Sentence Transformers.

### 3. Launch Web Interface

```bash
make web
```

Visit **http://localhost:8000** to:
- View recent articles sorted by relevance
- Vote on article relevance (▲ relevant, ▼ not relevant)
- See vote counts from all team members
- Filter by your votes

### 4. Train the Model

After labeling some articles:

```bash
make train
```

View training results at **http://localhost:5000** (MLflow UI)

## Daily Workflow

### Morning Briefing

```bash
make ingest       # Get latest news
make embed        # Process new articles
make web          # Review and vote
```

### Weekly Model Update

```bash
make train        # Retrain with new labels
```

## Keyboard Shortcuts (Web UI)

- **Click article** - Expand/collapse (removed in latest version - all content shown)
- **▲/▼ buttons** - Quick vote
- **Filter buttons** - Show all/relevant/not relevant/unlabeled

## Troubleshooting

### Docker containers not starting

```bash
# Check Docker is running
docker ps

# Restart containers
make stop
make start
```

### Database connection errors

```bash
# Reset database
docker compose -f config/docker-compose.yml down -v
make setup
```

### Port 8000 already in use

```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or change port in config/config.py
export WEB_PORT=8001
make web
```

### MLflow UI not accessible

```bash
# Check MLflow is running
docker compose -f config/docker-compose.yml ps

# Restart MLflow
docker compose -f config/docker-compose.yml restart mlflow
```

## Next Steps

- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md) for Kubernetes deployment
- **Configuration**: Edit [config/config.py](config/config.py) to add RSS feeds
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development guide

## Getting Help

- 📖 [Full README](README.md)
- 🐛 [Report Issues](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

## What's Next?

Once you're comfortable with the basics:

1. **Add your own RSS feeds** in `config/config.py`
2. **Deploy to Kubernetes** with `kubectl apply -f k8s/`
3. **Set up automated ingestion** with CronJobs
4. **Integrate with n8n** for custom workflows

Happy triaging! 🛡️
