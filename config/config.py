"""
Centralized configuration for the cybersecurity news triage system.
"""

import os

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "mlflow_db"),
    "user": os.getenv("DB_USER", "mlflow_user"),
    "password": os.getenv("DB_PASSWORD", "mlflow_password"),
}

# MLflow Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "Cybersecurity Signal Triage"

# Embedding Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
EMBEDDING_BATCH_SIZE = 32

# RSS Feed Sources
RSS_FEEDS = {
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "TheHackerNews": "https://feeds.feedburner.com/TheHackersNews",
    "SecurityWeek": "https://www.securityweek.com/feed/",
    "KrebsOnSecurity": "https://krebsonsecurity.com/feed/",
    "DarkReading": "https://www.darkreading.com/rss.xml",
}

# Web Application Configuration
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
WEB_DEBUG = os.getenv("WEB_DEBUG", "True").lower() == "true"

# Training Configuration
TRAIN_TEST_SPLIT = 0.2
RANDOM_STATE = 42
MODEL_TYPE = "logistic"  # Options: logistic, random_forest
