# AI-Driven Cybersecurity Signal Triage Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

An end-to-end machine learning system that learns to rank and classify cybersecurity news by relevance through collaborative human feedback.

![Platform Screenshot](docs/screenshot.png)
*Multi-user voting interface with real-time vote aggregation*

## Overview

This system reduces time spent manually scanning cybersecurity news by:
- Ingesting news from multiple sources (RSS feeds, n8n workflows)
- Generating semantic embeddings using Sentence Transformers
- Training ML models to predict relevance based on multi-user voting
- Continuously improving through active learning
- Providing a collaborative web interface for team-based article review

## Architecture

```
News Sources (RSS/n8n) → PostgreSQL → Embeddings → ML Model → Predictions
                              ↓
                    Web UI (Human Feedback)
                              ↓
                    MLflow (Training & Tracking)
```

## Components

- **PostgreSQL**: Stores news items, embeddings, predictions, and multi-user feedback
- **MLflow**: Experiment tracking and model registry
- **Web UI**: Collaborative voting interface with real-time vote counts
- **Training Pipeline**: Scikit-learn models trained on labeled data
- **Embedding Service**: Sentence Transformers for semantic text representation

## Key Features

- **Multi-User Voting**: Multiple team members can vote on article relevance
- **Vote Aggregation**: See upvote/downvote counts from all users
- **Smart Sorting**: Articles sorted by relevance votes
- **User Tracking**: Cookie-based user identification (no login required)
- **Kubernetes Ready**: Deploy to GKE, EKS, AKS, or local K8s clusters
- **Automated Workflows**: CronJobs for ingestion, embedding, and training

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd mlflow-project
```

2. Complete setup in one command:
```bash
make setup
```

This will:
- Install dependencies
- Start Docker infrastructure (PostgreSQL + MLflow)
- Initialize the database schema

### Usage

#### Quick Start with Make

```bash
make ingest    # Fetch news from RSS feeds
make embed     # Generate embeddings
make web       # Launch web UI for labeling (http://localhost:8000)
make train     # Train the model
make status    # Check database stats
```

#### Individual Commands

**1. Ingest News Articles**

From RSS feeds:
```bash
make ingest
# or: uv run python src/scripts/ingest_news.py
```

From n8n workflow: See [docs/n8n-integration.md](docs/n8n-integration.md)

**2. Generate Embeddings**

```bash
make embed
# or: uv run python src/scripts/generate_embeddings.py
```

Creates 384-dimensional embeddings using `all-MiniLM-L6-v2`.

**3. Label Articles**

Web Interface (Recommended):
```bash
make web
# or: uv run python src/web/app.py
```

Visit http://localhost:8000 to:
- View recent articles sorted by relevance votes
- Vote on article relevance (▲ relevant, ▼ not relevant)
- See vote counts from all team members
- Filter by your votes or unlabeled articles

CLI Interface (Single User):
```bash
make label
# or: uv run python src/scripts/label_news.py
```

**4. Train the Model**

```bash
make train
# or: uv run python src/scripts/train.py
```

**5. View Experiments**

Open http://localhost:5000 to see MLflow UI with:
- Model metrics (accuracy, precision, recall, F1)
- Training parameters
- Model artifacts
- Experiment comparison

**6. Check Status**

```bash
make status
# or: uv run python src/scripts/db_status.py
```

## Project Structure

```
mlflow-project/
├── config/
│   ├── config.py              # Centralized configuration
│   ├── docker-compose.yml     # Infrastructure setup (PostgreSQL + MLflow)
│   └── schema.sql             # Database schema
├── src/
│   ├── scripts/               # Main Python scripts
│   │   ├── init_db.py         # Database initialization
│   │   ├── ingest_news.py     # RSS feed scraper
│   │   ├── generate_embeddings.py  # Embedding generation
│   │   ├── label_news.py      # CLI labeling tool
│   │   ├── train.py           # Model training pipeline
│   │   └── db_status.py       # Database statistics
│   └── web/                   # Web application
│       ├── app.py             # Flask app (multi-user voting)
│       └── templates/         # HTML templates
│           ├── home.html      # Main voting interface
│           └── label.html     # Focused labeling interface
├── k8s/                       # Kubernetes manifests
│   ├── postgres.yaml          # PostgreSQL deployment
│   ├── mlflow.yaml            # MLflow server
│   ├── web-app.yaml           # Flask web app
│   └── cronjobs.yaml          # Automated jobs
├── docs/
│   ├── gke-deployment.md      # GKE deployment guide
│   └── n8n-integration.md     # n8n integration guide
├── Dockerfile                 # Container image
├── Makefile                   # Common commands
├── run.py                     # CLI task runner
├── pyproject.toml             # Python dependencies
├── DEPLOYMENT.md              # Multi-environment deployment
├── SETUP.md                   # Initial setup guide
└── README.md                  # This file
```

## Configuration

All configuration is centralized in [config/config.py](config/config.py).

### Environment Variables

You can override defaults using environment variables:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=mlflow_db
export DB_USER=mlflow_user
export DB_PASSWORD=mlflow_password
export MLFLOW_TRACKING_URI=http://localhost:5000
export WEB_HOST=0.0.0.0
export WEB_PORT=8000
```

Or create a `.env` file (not committed to git):

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mlflow_db
DB_USER=mlflow_user
DB_PASSWORD=mlflow_password
```

### RSS Feeds

Edit `RSS_FEEDS` in [config/config.py](config/config.py) to add/remove sources:

```python
RSS_FEEDS = {
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "TheHackerNews": "https://feeds.feedburner.com/TheHackersNews",
    # Add your sources here
}
```

### n8n Integration

To integrate with n8n workflows:

1. Create a webhook or HTTP endpoint in your n8n workflow
2. POST articles to PostgreSQL using the `news_items` table schema
3. Run `generate_embeddings.py` periodically to process new items

Example n8n node configuration available in `docs/n8n-integration.md`.

## Deployment

### Local Development (Docker Compose)

Already configured! Just run:
```bash
make setup
make web
```

### Production (Kubernetes)

Deploy to GKE, EKS, AKS, or any Kubernetes cluster:

```bash
# See DEPLOYMENT.md for full instructions
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/mlflow.yaml
kubectl apply -f k8s/web-app.yaml
kubectl apply -f k8s/cronjobs.yaml
```

Features:
- Auto-scaling web servers
- Automated hourly news ingestion
- Automated hourly embedding generation
- Weekly model retraining
- Persistent storage for DB and models

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guides.

## Development Roadmap

### Phase 1 ✅ (Completed)
- ✅ Data ingestion (RSS feeds)
- ✅ Embedding generation
- ✅ Simple relevance classifier
- ✅ MLflow integration
- ✅ Web labeling interface
- ✅ Multi-user voting system
- ✅ Kubernetes deployment manifests
- ✅ Vote aggregation and sorting

### Phase 2 (In Progress)
- [ ] n8n webhook integration
- [ ] Automated retraining pipeline
- [ ] Model performance monitoring
- [ ] Email/Slack notifications for high-relevance articles

### Phase 3 (Planned)
- [ ] Active learning (smart sample selection)
- [ ] Model drift detection
- [ ] API for inference service
- [ ] Advanced analytics dashboard

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [your-repo-url]/issues
- Documentation: [your-repo-url]/wiki
