# Quick Reference Guide

Fast lookup for common tasks and commands.

## 🚀 Getting Started

### Local Development
```bash
make setup    # Install + start infrastructure + init DB
make ingest   # Fetch news articles
make embed    # Generate embeddings
make web      # Launch UI at http://localhost:8000
make train    # Train model
```

### GKE Deployment
```bash
# See: docs/GKE_N8N_POSTGRESQL_SETUP.md
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/mlflow.yaml
kubectl apply -f k8s/web-app.yaml
kubectl apply -f k8s/cronjobs.yaml
```

---

## 📚 Documentation Map

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [README.md](../README.md) | Main overview | First time reading |
| [QUICKSTART.md](../QUICKSTART.md) | 5-minute setup | Getting started locally |
| [SETUP.md](../SETUP.md) | Detailed setup | Troubleshooting setup |
| [DEPLOYMENT.md](../DEPLOYMENT.md) | Multi-environment | Deploying to prod |
| [gke-deployment.md](gke-deployment.md) | GKE specific | GKE deployment |
| [GKE_N8N_POSTGRESQL_SETUP.md](GKE_N8N_POSTGRESQL_SETUP.md) | n8n + PostgreSQL on GKE | Setting up shared database |
| [N8N_MIGRATION_GUIDE.md](N8N_MIGRATION_GUIDE.md) | Migrate from n8n tables | Moving from internal tables |
| [n8n-integration.md](n8n-integration.md) | n8n workflows | Configuring n8n |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Developer guide | Contributing code |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Current state | Understanding project |

---

## 🗄️ Database

### Connection Details (Local)
```bash
Host: localhost
Port: 5432
Database: mlflow_db
User: mlflow_user
Password: mlflow_password
```

### Connection Details (GKE)
```bash
# From within cluster
Host: postgres
Port: 5432

# From different namespace
Host: postgres.default.svc.cluster.local
Port: 5432
```

### Quick Queries
```sql
-- Count articles
SELECT COUNT(*) FROM news_items;

-- Recent articles
SELECT id, source, title, published_at
FROM news_items
ORDER BY published_at DESC
LIMIT 10;

-- Articles by source
SELECT source, COUNT(*)
FROM news_items
GROUP BY source;

-- Labeling progress
SELECT
  COUNT(*) as total_articles,
  COUNT(DISTINCT f.news_item_id) as labeled,
  COUNT(*) - COUNT(DISTINCT f.news_item_id) as remaining
FROM news_items n
LEFT JOIN feedback f ON n.id = f.news_item_id;

-- Vote counts
SELECT
  n.title,
  COUNT(CASE WHEN f.label = 'relevant' THEN 1 END) as upvotes,
  COUNT(CASE WHEN f.label = 'not_relevant' THEN 1 END) as downvotes
FROM news_items n
LEFT JOIN feedback f ON n.id = f.news_item_id
GROUP BY n.id, n.title
ORDER BY upvotes DESC
LIMIT 10;
```

---

## 🔧 Common Tasks

### Check Status
```bash
# Local
make status

# GKE
kubectl exec -it <web-pod> -- python src/scripts/db_status.py
```

### Manual Jobs (GKE)
```bash
# Ingest news
kubectl create job --from=cronjob/news-ingestion manual-ingest-1

# Generate embeddings
kubectl create job --from=cronjob/embedding-generation manual-embed-1

# Train model
kubectl create job --from=cronjob/model-training manual-train-1

# Check job logs
kubectl logs job/<job-name> -f
```

### Access Services
```bash
# Local
Web UI:  http://localhost:8000
MLflow:  http://localhost:5000
PostgreSQL: localhost:5432

# GKE - Get external IPs
kubectl get svc news-triage-web
kubectl get svc mlflow
```

### Port Forwarding (GKE)
```bash
# Web UI
kubectl port-forward svc/news-triage-web 8000:80

# MLflow
kubectl port-forward svc/mlflow 5000:5000

# PostgreSQL
kubectl port-forward svc/postgres 5432:5432
```

---

## 🐛 Troubleshooting

### Database Issues

**Can't connect to PostgreSQL**
```bash
# Local
docker compose -f config/docker-compose.yml ps
docker compose -f config/docker-compose.yml logs postgres

# GKE
kubectl get pods -l app=postgres
kubectl logs -l app=postgres
```

**Tables don't exist**
```bash
# Local
uv run python src/scripts/init_db.py

# GKE
kubectl exec -it <web-pod> -- python src/scripts/init_db.py
```

### Web UI Issues

**Site can't be reached**
```bash
# Check if running
ps aux | grep "python src/web/app.py"

# Restart
pkill -f "python src/web/app.py"
make web
```

**Articles not showing**
```bash
# Check database
psql -h localhost -U mlflow_user -d mlflow_db -c \
  "SELECT COUNT(*) FROM news_items WHERE published_at > NOW() - INTERVAL '7 days';"

# Default filter is last 7 days
```

### n8n Issues

**Can't connect to PostgreSQL from n8n**
```bash
# Test from n8n pod
N8N_POD=$(kubectl get pod -l app=n8n -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $N8N_POD -- nc -zv postgres 5432
```

**Articles not appearing**
```bash
# Check if inserted
kubectl exec -it <postgres-pod> -- psql -U mlflow_user -d mlflow_db -c \
  "SELECT * FROM news_items ORDER BY id DESC LIMIT 5;"
```

---

## 🔑 Environment Variables

### All Configurable Settings
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mlflow_db
DB_USER=mlflow_user
DB_PASSWORD=mlflow_password

# Web Server
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_DEBUG=False

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# RSS Feeds (edit config/config.py)
```

---

## 📦 Kubernetes Resources

### Get Resource Status
```bash
# Pods
kubectl get pods

# Services
kubectl get svc

# PersistentVolumes
kubectl get pv
kubectl get pvc

# CronJobs
kubectl get cronjobs

# Recent Jobs
kubectl get jobs --sort-by=.metadata.creationTimestamp

# Events
kubectl get events --sort-by='.lastTimestamp'
```

### Scaling
```bash
# Scale web app
kubectl scale deployment news-triage-web --replicas=5

# Auto-scale
kubectl autoscale deployment news-triage-web \
  --cpu-percent=70 --min=2 --max=10
```

### Logs
```bash
# Web app
kubectl logs -l app=news-triage-web -f

# PostgreSQL
kubectl logs -l app=postgres -f

# MLflow
kubectl logs -l app=mlflow -f

# CronJob (latest)
kubectl logs -l job-name=<job-name> -f
```

---

## 🔐 Security

### Change Default Password
```bash
# Update in kubernetes secret
kubectl delete secret postgres-secret
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD='new-secure-password'

# Restart pods to pick up new secret
kubectl rollout restart deployment/news-triage-web
kubectl rollout restart deployment/mlflow
kubectl rollout restart statefulset/postgres  # if using statefulset
```

### Database Access
```bash
# Create read-only user
kubectl exec -it <postgres-pod> -- psql -U mlflow_user -d mlflow_db << EOF
CREATE USER readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE mlflow_db TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
EOF
```

---

## 📊 Monitoring

### Key Metrics to Watch

```sql
-- Article ingestion rate
SELECT
  DATE(created_at) as date,
  COUNT(*) as articles_added
FROM news_items
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Labeling velocity
SELECT
  DATE(created_at) as date,
  COUNT(*) as labels_added
FROM feedback
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Model performance (check MLflow UI)
-- Storage usage
SELECT
  pg_size_pretty(pg_database_size('mlflow_db')) as database_size;
```

---

## 🆘 Getting Help

### Logs Location
```bash
# Local
./*.log
/tmp/mlflow-*.log

# GKE
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Previous pod instance
```

### Debug Mode
```bash
# Enable debug logging (local)
export WEB_DEBUG=True
make web

# Enable debug logging (GKE)
# Edit deployment env: WEB_DEBUG=True
kubectl set env deployment/news-triage-web WEB_DEBUG=True
```

### Health Checks
```bash
# Web app
curl http://localhost:8000/

# MLflow
curl http://localhost:5000/

# Database
psql -h localhost -U mlflow_user -d mlflow_db -c "SELECT 1;"
```

---

## 🔄 Backup & Restore

### Backup Database
```bash
# Local
pg_dump -h localhost -U mlflow_user mlflow_db > backup.sql

# GKE
kubectl exec -it <postgres-pod> -- \
  pg_dump -U mlflow_user mlflow_db > backup.sql

# Upload to GCS
gsutil cp backup.sql gs://your-bucket/backups/backup-$(date +%Y%m%d).sql
```

### Restore Database
```bash
# Local
psql -h localhost -U mlflow_user -d mlflow_db < backup.sql

# GKE
kubectl exec -i <postgres-pod> -- \
  psql -U mlflow_user -d mlflow_db < backup.sql
```

---

## 📞 Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

---

*Last updated: 2025-12-26*
