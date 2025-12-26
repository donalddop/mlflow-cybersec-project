## GKE Deployment Guide

This guide shows how to deploy the cybersecurity news triage system to Google Kubernetes Engine (GKE).

## Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and configured
- `kubectl` installed
- Docker installed locally

## Quick Start

### 1. Set up GKE Cluster

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
export CLUSTER_NAME="news-triage-cluster"
export REGION="us-central1"

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Create GKE cluster
gcloud container clusters create $CLUSTER_NAME \
  --region $REGION \
  --num-nodes 2 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 4 \
  --enable-autorepair \
  --enable-autoupgrade

# Get credentials
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION
```

### 2. Build and Push Docker Image

```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/news-triage-web:latest .

# Configure Docker for GCR
gcloud auth configure-docker

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/news-triage-web:latest
```

### 3. Update Kubernetes Manifests

Update `k8s/web-app.yaml` and `k8s/cronjobs.yaml` to use your image:

```bash
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/web-app.yaml
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/cronjobs.yaml
```

### 4. Deploy to GKE

```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgres.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# Deploy MLflow
kubectl apply -f k8s/mlflow.yaml

# Wait for MLflow to be ready
kubectl wait --for=condition=ready pod -l app=mlflow --timeout=300s

# Deploy web application
kubectl apply -f k8s/web-app.yaml

# Deploy CronJobs (optional - for automated ingestion)
kubectl apply -f k8s/cronjobs.yaml
```

### 5. Initialize Database

```bash
# Get a pod name
POD=$(kubectl get pod -l app=news-triage-web -o jsonpath='{.items[0].metadata.name}')

# Run database initialization
kubectl exec -it $POD -- uv run python src/scripts/init_db.py

# Run initial ingestion
kubectl exec -it $POD -- uv run python src/scripts/ingest_news.py

# Generate embeddings
kubectl exec -it $POD -- uv run python src/scripts/generate_embeddings.py
```

### 6. Access the Application

```bash
# Get the external IP
kubectl get service news-triage-web

# Or use port-forward for testing
kubectl port-forward service/news-triage-web 8000:80
```

## Environment-Specific Deployments

### Development Environment

```bash
# Use smaller resources and LoadBalancer for easy access
kubectl apply -f k8s/ --namespace=dev
```

### Staging Environment

```bash
# Create staging namespace
kubectl create namespace staging

# Deploy with staging configuration
kubectl apply -f k8s/ --namespace=staging
```

### Production Environment

```bash
# Create production namespace
kubectl create namespace production

# Use production secrets
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD='your-strong-password' \
  --namespace=production

# Deploy
kubectl apply -f k8s/ --namespace=production
```

## Using Ingress (Recommended for Production)

### 1. Install NGINX Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

### 2. Create Ingress Resource

Create `k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: news-triage-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod  # If using cert-manager
spec:
  rules:
  - host: news-triage.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: news-triage-web
            port:
              number: 80
  - host: mlflow.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mlflow
            port:
              number: 5000
```

Apply the ingress:

```bash
kubectl apply -f k8s/ingress.yaml
```

## Configuration Management

### Using ConfigMaps

```bash
# Create ConfigMap for application config
kubectl create configmap app-config \
  --from-file=config/config.py
```

### Using Secrets

```bash
# Create secret for sensitive data
kubectl create secret generic db-credentials \
  --from-literal=username=mlflow_user \
  --from-literal=password='your-secure-password'
```

## Automated Deployment with Cloud Build

Create `cloudbuild.yaml`:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/news-triage-web:$COMMIT_SHA', '.']

  # Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/news-triage-web:$COMMIT_SHA']

  # Deploy to GKE
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args:
      - run
      - --filename=k8s/
      - --image=gcr.io/$PROJECT_ID/news-triage-web:$COMMIT_SHA
      - --location=$_REGION
      - --cluster=$_CLUSTER_NAME
```

Set up trigger:

```bash
gcloud builds triggers create github \
  --repo-name=news-triage \
  --repo-owner=your-github-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## Monitoring and Logging

### View Logs

```bash
# Web app logs
kubectl logs -l app=news-triage-web -f

# MLflow logs
kubectl logs -l app=mlflow -f

# PostgreSQL logs
kubectl logs -l app=postgres -f

# CronJob logs
kubectl logs -l job-name=news-ingestion
```

### Monitoring

```bash
# Install Prometheus and Grafana (optional)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack
```

## Scaling

### Manual Scaling

```bash
# Scale web app
kubectl scale deployment news-triage-web --replicas=5

# Scale down
kubectl scale deployment news-triage-web --replicas=2
```

### Horizontal Pod Autoscaler

```bash
kubectl autoscale deployment news-triage-web \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

## Backup and Restore

### Backup PostgreSQL

```bash
# Create backup
kubectl exec -it $(kubectl get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- \
  pg_dump -U mlflow_user mlflow_db > backup.sql

# Upload to GCS
gsutil cp backup.sql gs://your-bucket/backups/backup-$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
# Download from GCS
gsutil cp gs://your-bucket/backups/backup-20240101.sql backup.sql

# Restore
kubectl exec -i $(kubectl get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- \
  psql -U mlflow_user mlflow_db < backup.sql
```

## Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Database connection issues

```bash
# Test connection from web app pod
kubectl exec -it <web-pod> -- \
  psql -h postgres -U mlflow_user -d mlflow_db
```

### Image pull errors

```bash
# Verify image exists
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Check pod events
kubectl get events --sort-by='.lastTimestamp'
```

## Cost Optimization

1. **Use Preemptible Nodes**: 80% cheaper
```bash
gcloud container node-pools create preemptible-pool \
  --cluster=$CLUSTER_NAME \
  --preemptible \
  --machine-type=n1-standard-2
```

2. **Use Autopilot** (managed GKE):
```bash
gcloud container clusters create-auto $CLUSTER_NAME \
  --region=$REGION
```

3. **Set Resource Limits**: Update deployment manifests with appropriate limits

4. **Use Cloud Storage for Artifacts**: Instead of persistent volumes

## Security Best Practices

1. **Use Workload Identity** for GCP API access
2. **Enable Network Policies** for pod-to-pod communication
3. **Use Secrets** for sensitive data
4. **Enable Pod Security Policies**
5. **Regular Updates**: Keep GKE and images updated
6. **Use Private GKE Cluster** for production

## Next Steps

1. Set up CI/CD pipeline with Cloud Build
2. Configure monitoring and alerting
3. Set up automated backups
4. Configure SSL certificates with cert-manager
5. Implement authentication (OAuth, IAP)
