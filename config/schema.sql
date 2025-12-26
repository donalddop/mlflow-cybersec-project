-- Cybersecurity Signal Triage Database Schema

-- Raw news items from various sources
CREATE TABLE IF NOT EXISTS news_items (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,  -- e.g., 'SecurityWeek', 'BleepingComputer'
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    published_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB  -- Store additional fields like author, tags, etc.
);

-- Text embeddings for news items
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    news_item_id INTEGER REFERENCES news_items(id) ON DELETE CASCADE,
    embedding_model VARCHAR(255) NOT NULL,  -- e.g., 'all-MiniLM-L6-v2'
    embedding FLOAT8[] NOT NULL,  -- Store as array of floats
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(news_item_id, embedding_model)
);

-- Model predictions / relevance scores
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    news_item_id INTEGER REFERENCES news_items(id) ON DELETE CASCADE,
    model_version VARCHAR(255) NOT NULL,  -- MLflow run_id or model version
    relevance_score FLOAT NOT NULL,  -- 0.0 to 1.0
    prediction_class VARCHAR(50),  -- e.g., 'relevant', 'not_relevant'
    confidence FLOAT,
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB  -- Store additional prediction details
);

-- Human feedback for training
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    news_item_id INTEGER REFERENCES news_items(id) ON DELETE CASCADE,
    label VARCHAR(50) NOT NULL,  -- e.g., 'relevant', 'not_relevant'
    user_id VARCHAR(255),  -- Optional: track who provided feedback
    notes TEXT,  -- Optional: additional context
    tags TEXT[],  -- Optional: categorization tags
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_items_source ON news_items(source);
CREATE INDEX IF NOT EXISTS idx_news_items_scraped_at ON news_items(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_news_item_id ON embeddings(news_item_id);
CREATE INDEX IF NOT EXISTS idx_predictions_news_item_id ON predictions(news_item_id);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted_at ON predictions(predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_news_item_id ON feedback(news_item_id);
CREATE INDEX IF NOT EXISTS idx_feedback_label ON feedback(label);
