.PHONY: help install start stop init-db ingest embed label train web status clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with uv
	uv sync

start:  ## Start Docker infrastructure (PostgreSQL + MLflow)
	docker-compose -f config/docker-compose.yml up -d
	@echo "✅ Infrastructure started"
	@echo "   PostgreSQL: localhost:5432"
	@echo "   MLflow UI:  http://localhost:5000"

stop:  ## Stop Docker infrastructure
	docker-compose -f config/docker-compose.yml down

init-db:  ## Initialize database schema
	uv run python src/scripts/init_db.py

ingest:  ## Ingest news from RSS feeds
	uv run python src/scripts/ingest_news.py

embed:  ## Generate embeddings for news articles
	uv run python src/scripts/generate_embeddings.py

label:  ## Launch CLI labeling tool
	uv run python src/scripts/label_news.py

train:  ## Train the relevance classifier
	uv run python src/scripts/train.py

web:  ## Launch web labeling interface
	@echo "🚀 Starting web interface..."
	@echo "   URL: http://localhost:8000"
	uv run python src/web/app.py

status:  ## Show database statistics
	uv run python src/scripts/db_status.py

clean:  ## Clean Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

setup: install start init-db  ## Complete setup (install + start + init-db)
	@echo "✅ Setup complete! Run 'make ingest' to fetch news articles"

pipeline: ingest embed  ## Run full data pipeline (ingest + embed)
	@echo "✅ Data pipeline complete! Run 'make web' to label articles"
