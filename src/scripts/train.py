"""
Train a cybersecurity news relevance classifier using labeled data and embeddings.

This script:
1. Loads labeled news items and their embeddings from the database
2. Trains a classification model to predict relevance
3. Logs the model, parameters, and metrics to MLflow
"""

import mlflow
import mlflow.sklearn
import psycopg2
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mlflow_db",
    "user": "mlflow_user",
    "password": "mlflow_password",
}

# MLflow configuration
mlflow.set_tracking_uri("http://localhost:5000")
experiment_name = "Cybersecurity Signal Triage v2"
mlflow.set_experiment(experiment_name)


def load_training_data():
    """Load labeled news items with their embeddings from the database."""
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    e.embedding,
                    f.label,
                    n.title
                FROM embeddings e
                JOIN news_items n ON e.news_item_id = n.id
                JOIN feedback f ON n.id = f.news_item_id
                WHERE f.label IN ('relevant', 'not_relevant')
                ORDER BY f.created_at
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        raise ValueError("No labeled training data found. Please run label_news.py first.")

    # Extract features (embeddings) and labels
    X = np.array([row[0] for row in rows])
    y = np.array([1 if row[1] == 'relevant' else 0 for row in rows])
    titles = [row[2] for row in rows]

    print(f"Loaded {len(X)} labeled samples")
    print(f"  - Relevant: {np.sum(y)} ({100*np.mean(y):.1f}%)")
    print(f"  - Not relevant: {len(y) - np.sum(y)} ({100*(1-np.mean(y)):.1f}%)")
    print(f"  - Embedding dimension: {X.shape[1]}")

    return X, y, titles


def train_model(X_train, y_train, model_type='logistic'):
    """Train a classification model."""
    if model_type == 'logistic':
        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced',  # Handle imbalanced classes
            C=1.0
        )
    elif model_type == 'random_forest':
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test):
    """Evaluate model and return metrics."""
    y_pred = model.predict(X_test)

    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1_score': f1_score(y_test, y_pred, zero_division=0),
    }

    # Also compute metrics for the minority class (relevant)
    if len(np.unique(y_test)) > 1:
        metrics['precision_relevant'] = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
        metrics['recall_relevant'] = recall_score(y_test, y_pred, pos_label=1, zero_division=0)

    return metrics, y_pred


def main():
    """Main training pipeline."""
    print(f"Using experiment: '{experiment_name}'")
    print("=" * 80)

    # Load data
    print("\n1. Loading training data...")
    X, y, titles = load_training_data()

    # Split data
    print("\n2. Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test, titles_train, titles_test = train_test_split(
        X, y, titles, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  - Training set: {len(X_train)} samples")
    print(f"  - Test set: {len(X_test)} samples")

    # Start MLflow run
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"\n3. Starting MLflow run: {run_id}")

        # Log parameters
        params = {
            'model_type': 'logistic',
            'embedding_model': 'all-MiniLM-L6-v2',
            'train_size': len(X_train),
            'test_size': len(X_test),
            'test_split': 0.2,
            'class_weight': 'balanced',
            'random_state': 42,
        }
        mlflow.log_params(params)

        # Train model
        print("\n4. Training model...")
        model = train_model(X_train, y_train, model_type=params['model_type'])

        # Evaluate on training set
        print("\n5. Evaluating model...")
        train_metrics, _ = evaluate_model(model, X_train, y_train)
        test_metrics, y_pred = evaluate_model(model, X_test, y_test)

        # Log metrics
        for key, value in train_metrics.items():
            mlflow.log_metric(f"train_{key}", value)
        for key, value in test_metrics.items():
            mlflow.log_metric(f"test_{key}", value)

        # Print results
        print("\nTraining Metrics:")
        for key, value in train_metrics.items():
            print(f"  {key}: {value:.4f}")

        print("\nTest Metrics:")
        for key, value in test_metrics.items():
            print(f"  {key}: {value:.4f}")

        # Show classification report
        print("\nDetailed Classification Report (Test Set):")
        print(classification_report(y_test, y_pred, target_names=['Not Relevant', 'Relevant']))

        # Show some predictions
        print("\nSample Predictions on Test Set:")
        for i in range(min(5, len(y_test))):
            actual = "Relevant" if y_test[i] == 1 else "Not Relevant"
            predicted = "Relevant" if y_pred[i] == 1 else "Not Relevant"
            correct = "✓" if y_test[i] == y_pred[i] else "✗"
            print(f"{correct} {titles_test[i][:60]}...")
            print(f"  Actual: {actual}, Predicted: {predicted}\n")

        # Log model
        print("6. Logging model to MLflow...")
        mlflow.sklearn.log_model(model, "relevance-classifier")

        print("\n✅ Training complete!")
        print(f"\nView this run in MLflow UI:")
        print(f"http://localhost:5000/#/experiments/{run.info.experiment_id}/runs/{run_id}")


if __name__ == "__main__":
    main()
