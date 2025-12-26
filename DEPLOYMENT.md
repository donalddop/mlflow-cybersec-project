# Deployment Guide

## Overview

This system is designed to run in multiple environments with minimal configuration changes.

## Deployment Options

### 1. Local Development (Docker Compose)

**Best for**: Local development and testing

```bash
# Start infrastructure
docker-compose -f config/docker-compose.yml up -d

# Initialize and run
uv sync
uv run python run.py init-db
uv run python run.py ingest
uv run python run.py embed
uv run python run.py web
```

**Access**:
- Web UI: http://localhost:8000
- MLflow: http://localhost:5000
- PostgreSQL: localhost:5432

---

### 2. Google Kubernetes Engine (GKE)

**Best for**: Production deployment, team collaboration

See detailed guide: [docs/gke-deployment.md](docs/gke-deployment.md)

**Quick Deploy**:

```bash
# 1. Build and push image
export PROJECT_ID="your-gcp-project"
docker build -t gcr.io/$PROJECT_ID/news-triage-web:latest .
docker push gcr.io/$PROJECT_ID/news-triage-web:latest

# 2. Update manifests
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/*.yaml

# 3. Deploy
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/mlflow.yaml
kubectl apply -f k8s/web-app.yaml
kubectl apply -f k8s/cronjobs.yaml  # Optional: automated ingestion

# 4. Initialize
POD=$(kubectl get pod -l app=news-triage-web -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -- uv run python src/scripts/init_db.py
```

**Features**:
- ✅ Auto-scaling web servers
- ✅ Automated news ingestion (hourly)
- ✅ Automated embedding generation (hourly)
- ✅ Weekly model retraining
- ✅ Persistent storage for DB and models
- ✅ Load balancing
- ✅ Easy rollbacks

---

### 3. Other Kubernetes Environments

**Works on**:
- Amazon EKS
- Azure AKS
- On-premise Kubernetes
- Minikube (local testing)

Just update the image registry in `k8s/*.yaml`:

```yaml
# For Docker Hub
image: yourusername/news-triage-web:latest

# For AWS ECR
image: account.dkr.ecr.region.amazonaws.com/news-triage-web:latest

# For Azure ACR
image: yourregistry.azurecr.io/news-triage-web:latest
```

---

## Environment-Specific Configuration

### Development

```bash
# .env.dev
DB_HOST=localhost
DB_PORT=5432
WEB_DEBUG=True
WEB_PORT=8000
```

### Staging

```bash
# .env.staging
DB_HOST=postgres.staging.svc.cluster.local
DB_PORT=5432
WEB_DEBUG=False
WEB_PORT=8000
MLFLOW_TRACKING_URI=http://mlflow.staging.svc.cluster.local:5000
```

### Production

```bash
# .env.production
DB_HOST=postgres.production.svc.cluster.local
DB_PORT=5432
WEB_DEBUG=False
WEB_PORT=8000
MLFLOW_TRACKING_URI=http://mlflow.production.svc.cluster.local:5000
```

---

## CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build image
        run: |
          docker build -t gcr.io/${{ secrets.GCP_PROJECT }}/news-triage-web:${{ github.sha }} .

      - name: Push to GCR
        run: |
          gcloud auth configure-docker
          docker push gcr.io/${{ secrets.GCP_PROJECT }}/news-triage-web:${{ github.sha }}

      - name: Deploy to GKE
        run: |
          gcloud container clusters get-credentials ${{ secrets.GKE_CLUSTER }} --region ${{ secrets.GKE_REGION }}
          kubectl set image deployment/news-triage-web web=gcr.io/${{ secrets.GCP_PROJECT }}/news-triage-web:${{ github.sha }}
```

---

## Multi-Environment Setup

### Option 1: Separate Clusters

```bash
# Dev cluster
gcloud container clusters create news-triage-dev --region us-central1

# Prod cluster
gcloud container clusters create news-triage-prod --region us-central1
```

### Option 2: Namespaces in Same Cluster

```bash
# Create namespaces
kubectl create namespace dev
kubectl create namespace staging
kubectl create namespace production

# Deploy to specific namespace
kubectl apply -f k8s/ --namespace=dev
kubectl apply -f k8s/ --namespace=production
```

---

## Database Migrations

When you update the schema:

```bash
# 1. Backup database
kubectl exec -it $(kubectl get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- \
  pg_dump -U mlflow_user mlflow_db > backup.sql

# 2. Apply new schema
kubectl exec -it <web-pod> -- uv run python src/scripts/init_db.py

# 3. If something goes wrong, restore:
kubectl exec -i $(kubectl get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- \
  psql -U mlflow_user mlflow_db < backup.sql
```

---

## Monitoring

### Logs

```bash
# Application logs
kubectl logs -l app=news-triage-web -f

# Database logs
kubectl logs -l app=postgres -f

# CronJob logs
kubectl get jobs
kubectl logs job/news-ingestion-<timestamp>
```

### Metrics

Access MLflow UI to monitor:
- Model performance over time
- Training metrics
- Experiment comparisons

---

## Troubleshooting

### Web app not accessible

```bash
# Check pod status
kubectl get pods -l app=news-triage-web

# Check logs
kubectl logs -l app=news-triage-web

# Port forward for testing
kubectl port-forward service/news-triage-web 8000:80
```

### Database connection failures

```bash
# Verify PostgreSQL is running
kubectl get pods -l app=postgres

# Test connection
kubectl exec -it <web-pod> -- \
  psql -h postgres -U mlflow_user -d mlflow_db -c "\dt"
```

### CronJobs not running

```bash
# Check CronJob status
kubectl get cronjobs

# Check recent jobs
kubectl get jobs --sort-by=.metadata.creationTimestamp

# Check logs
kubectl logs job/<job-name>
```

---

## Scaling

### Horizontal Scaling

```bash
# Manual scaling
kubectl scale deployment news-triage-web --replicas=5

# Auto-scaling
kubectl autoscale deployment news-triage-web \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

### Vertical Scaling

Update resource limits in `k8s/web-app.yaml`:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

---

## Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Use secrets for sensitive data
- [ ] Enable network policies
- [ ] Configure RBAC
- [ ] Use private container registry
- [ ] Enable SSL/TLS with Ingress
- [ ] Regular security updates
- [ ] Implement authentication (OAuth, LDAP)
- [ ] Enable audit logging
- [ ] Use Workload Identity (GKE)

---

## Cost Optimization

1. **Use preemptible/spot instances** for non-critical workloads
2. **Right-size resources** based on actual usage
3. **Use PersistentVolumes** instead of expensive storage
4. **Enable cluster autoscaling**
5. **Schedule training jobs** during off-peak hours
6. **Use GKE Autopilot** for managed infrastructure

---

## Backup Strategy

### Automated Backups

Add to CronJobs:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:13
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres -U mlflow_user mlflow_db | \
              gzip > /backup/backup-$(date +%Y%m%d).sql.gz
          restartPolicy: OnFailure
```

---

## Next Steps

1. ✅ Deploy to GKE dev environment
2. ✅ Test with real traffic
3. ✅ Set up monitoring and alerts
4. ✅ Configure CI/CD pipeline
5. ✅ Deploy to staging
6. ✅ Load testing
7. ✅ Deploy to production
8. ✅ Set up automated backups
