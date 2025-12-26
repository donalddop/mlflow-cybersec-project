# Setting Up PostgreSQL for n8n on GKE

This guide shows how to set up PostgreSQL in your GKE cluster to work with your existing n8n deployment.

## Overview

You'll set up:
1. PostgreSQL database in GKE (same cluster as n8n)
2. n8n connection to PostgreSQL
3. MLflow project connection to the same PostgreSQL

This creates a shared database that both n8n and the MLflow project can access.

---

## Prerequisites

- GKE cluster with n8n already running
- `kubectl` configured to access your cluster
- `gcloud` CLI installed

---

## Step 1: Create PostgreSQL in GKE

### Option A: Quick Setup (Development/Staging)

Use the PostgreSQL manifest from this project:

```bash
# 1. Download the PostgreSQL manifest
# (Already in your project at k8s/postgres.yaml)

# 2. Apply to your cluster
kubectl apply -f k8s/postgres.yaml

# 3. Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# 4. Verify it's running
kubectl get pods -l app=postgres
kubectl get svc postgres
```

This creates:
- PostgreSQL 13 deployment
- PersistentVolumeClaim (10Gi storage)
- Service named `postgres` (accessible at `postgres:5432` within cluster)

### Option B: Production Setup with Cloud SQL

For production, consider using Google Cloud SQL instead:

```bash
# 1. Create Cloud SQL instance
gcloud sql instances create mlflow-db \
  --database-version=POSTGRES_13 \
  --tier=db-f1-micro \
  --region=us-central1

# 2. Set password
gcloud sql users set-password postgres \
  --instance=mlflow-db \
  --password=your-secure-password

# 3. Create database
gcloud sql databases create mlflow_db --instance=mlflow-db

# 4. Create user
gcloud sql users create mlflow_user \
  --instance=mlflow-db \
  --password=your-secure-password

# 5. Get connection name
gcloud sql instances describe mlflow-db --format='value(connectionName)'
# Output: project-id:region:instance-name
```

**For Cloud SQL**, you'll need to use the [Cloud SQL Proxy](https://cloud.google.com/sql/docs/postgres/connect-kubernetes-engine) in your pods.

---

## Step 2: Initialize the Database

### Connect to PostgreSQL Pod

```bash
# Get the PostgreSQL pod name
POD_NAME=$(kubectl get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}')

# Connect to PostgreSQL
kubectl exec -it $POD_NAME -- psql -U mlflow_user -d mlflow_db
```

### Run Schema Initialization

Create a ConfigMap with the schema:

```bash
# Create ConfigMap from schema file
kubectl create configmap db-schema --from-file=config/schema.sql

# Create initialization job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: init-db
spec:
  template:
    spec:
      containers:
      - name: init
        image: postgres:13
        command:
        - psql
        - -h
        - postgres
        - -U
        - mlflow_user
        - -d
        - mlflow_db
        - -f
        - /schema/schema.sql
        env:
        - name: PGPASSWORD
          value: mlflow_password
        volumeMounts:
        - name: schema
          mountPath: /schema
      volumes:
      - name: schema
        configMap:
          name: db-schema
      restartPolicy: Never
  backoffLimit: 3
EOF

# Wait for job to complete
kubectl wait --for=condition=complete job/init-db --timeout=60s

# Check logs
kubectl logs job/init-db
```

### Verify Database Tables

```bash
# List tables
kubectl exec -it $POD_NAME -- psql -U mlflow_user -d mlflow_db -c "\dt"

# Should show:
#  Schema |     Name      | Type  |    Owner
# --------+---------------+-------+-------------
#  public | embeddings    | table | mlflow_user
#  public | feedback      | table | mlflow_user
#  public | news_items    | table | mlflow_user
#  public | predictions   | table | mlflow_user
```

---

## Step 3: Connect n8n to PostgreSQL

### Method 1: Update n8n Workflow (Preferred)

1. Open your n8n workflow
2. Add a **PostgreSQL** node where you currently save data
3. Create credentials:

**For In-Cluster PostgreSQL:**
```
Host: postgres
Port: 5432
Database: mlflow_db
User: mlflow_user
Password: mlflow_password
SSL: Disable
```

**For Cloud SQL:**
```
Host: 127.0.0.1  (using Cloud SQL Proxy)
Port: 5432
Database: mlflow_db
User: mlflow_user
Password: your-secure-password
SSL: Require
```

### Method 2: Use Kubernetes Secret

Create a secret for database credentials:

```bash
# Create secret
kubectl create secret generic postgres-credentials \
  --from-literal=POSTGRES_HOST=postgres \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=mlflow_db \
  --from-literal=POSTGRES_USER=mlflow_user \
  --from-literal=POSTGRES_PASSWORD=mlflow_password

# Verify secret
kubectl get secret postgres-credentials -o yaml
```

If n8n supports environment variables, mount this secret:

```yaml
# Add to n8n deployment
env:
- name: POSTGRES_HOST
  valueFrom:
    secretKeyRef:
      name: postgres-credentials
      key: POSTGRES_HOST
- name: POSTGRES_PORT
  valueFrom:
    secretKeyRef:
      name: postgres-credentials
      key: POSTGRES_PORT
# ... etc
```

---

## Step 4: Test the Connection from n8n

### Create a Test Workflow

1. In n8n, create a new workflow
2. Add a **PostgreSQL** node
3. Select operation: **Execute Query**
4. Query:
   ```sql
   SELECT COUNT(*) as count FROM news_items;
   ```
5. Execute the node

**Expected result:** Query succeeds (even if count is 0)

### Insert Test Data

Add another PostgreSQL node:

**Operation:** Insert

**Table:** news_items

**Data:**
```json
{
  "source": "n8n-test",
  "title": "Test Article",
  "content": "This is a test article from n8n",
  "url": "https://example.com/test-123",
  "published_at": "2025-12-26T12:00:00"
}
```

Execute and verify:

```bash
# Check if test article was inserted
kubectl exec -it $POD_NAME -- psql -U mlflow_user -d mlflow_db -c \
  "SELECT id, source, title FROM news_items WHERE source = 'n8n-test';"
```

---

## Step 5: Deploy MLflow Project to Same Cluster

Now deploy the web app to access the same database:

### Update web-app.yaml

The web app is already configured to use the `postgres` service:

```yaml
# k8s/web-app.yaml already has:
env:
- name: DB_HOST
  value: postgres  # ✅ Will connect to same PostgreSQL
- name: DB_PORT
  value: "5432"
- name: DB_NAME
  value: mlflow_db
- name: DB_USER
  value: mlflow_user
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: postgres-secret
      key: POSTGRES_PASSWORD
```

### Deploy Web App

```bash
# Build and push image
export PROJECT_ID="your-gcp-project-id"

docker build -t gcr.io/$PROJECT_ID/news-triage-web:latest .
docker push gcr.io/$PROJECT_ID/news-triage-web:latest

# Update manifests with your project ID
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/web-app.yaml
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/cronjobs.yaml

# Deploy MLflow (optional - for experiment tracking)
kubectl apply -f k8s/mlflow.yaml

# Deploy web app
kubectl apply -f k8s/web-app.yaml

# Wait for deployment
kubectl wait --for=condition=available deployment/news-triage-web --timeout=300s

# Get external IP
kubectl get service news-triage-web
```

---

## Step 6: Verify End-to-End Integration

### Test the Full Pipeline

1. **Trigger your n8n workflow** to ingest some articles
   ```bash
   # Check articles were inserted
   kubectl exec -it $POD_NAME -- psql -U mlflow_user -d mlflow_db -c \
     "SELECT COUNT(*) FROM news_items;"
   ```

2. **Access the web UI**
   ```bash
   # Get web app external IP
   kubectl get svc news-triage-web

   # Visit http://<EXTERNAL-IP>
   # You should see articles from n8n!
   ```

3. **Generate embeddings**
   ```bash
   # Run embedding generation job
   kubectl create job --from=cronjob/embedding-generation manual-embed-1

   # Check logs
   kubectl logs -l job-name=manual-embed-1 -f
   ```

4. **Vote on articles** in the web UI

5. **Train model**
   ```bash
   # Run training job
   kubectl create job --from=cronjob/model-training manual-train-1

   # Check logs
   kubectl logs -l job-name=manual-train-1 -f
   ```

---

## Namespace Considerations

### Same Namespace (Simplest)

If n8n and the MLflow project are in the same namespace:

```bash
# Everything works with service name "postgres"
DB_HOST=postgres
```

### Different Namespaces

If n8n is in a different namespace:

```bash
# From n8n's namespace, use fully qualified service name
DB_HOST=postgres.mlflow-namespace.svc.cluster.local
```

Update n8n credentials accordingly:
```
Host: postgres.default.svc.cluster.local  # Adjust namespace
Port: 5432
```

### Network Policies

If you have network policies enabled, ensure n8n can reach PostgreSQL:

```yaml
# Allow n8n to access PostgreSQL
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-n8n-to-postgres
spec:
  podSelector:
    matchLabels:
      app: postgres
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: n8n  # Adjust to your n8n label
    ports:
    - protocol: TCP
      port: 5432
```

---

## Troubleshooting

### n8n Can't Connect to PostgreSQL

**Error:** `Connection refused` or `Could not connect`

**Check 1:** Verify PostgreSQL is running
```bash
kubectl get pods -l app=postgres
kubectl get svc postgres
```

**Check 2:** Test connectivity from n8n pod
```bash
# Get n8n pod name
N8N_POD=$(kubectl get pod -l app=n8n -o jsonpath='{.items[0].metadata.name}')

# Test connection
kubectl exec -it $N8N_POD -- nc -zv postgres 5432

# Or try psql if available
kubectl exec -it $N8N_POD -- \
  psql -h postgres -U mlflow_user -d mlflow_db -c "SELECT 1;"
```

**Check 3:** Verify namespace
```bash
# If different namespaces, use FQDN
kubectl exec -it $N8N_POD -- \
  psql -h postgres.default.svc.cluster.local -U mlflow_user -d mlflow_db -c "SELECT 1;"
```

### Authentication Failed

**Error:** `password authentication failed`

**Solution:** Verify password in secret
```bash
kubectl get secret postgres-secret -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d
```

Update n8n credentials with correct password.

### Permission Denied

**Error:** `permission denied for table news_items`

**Solution:** Grant permissions
```bash
kubectl exec -it $POD_NAME -- psql -U mlflow_user -d mlflow_db -c \
  "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mlflow_user;"
```

### Database Not Found

**Error:** `database "mlflow_db" does not exist`

**Solution:** Create database
```bash
kubectl exec -it $POD_NAME -- psql -U postgres -c "CREATE DATABASE mlflow_db;"
kubectl exec -it $POD_NAME -- psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mlflow_db TO mlflow_user;"
```

### Tables Don't Exist

**Error:** `relation "news_items" does not exist`

**Solution:** Run schema initialization (see Step 2)

---

## Production Recommendations

### 1. Use Cloud SQL (Recommended)

Benefits:
- Managed backups
- High availability
- Automatic updates
- Better performance
- Point-in-time recovery

```bash
# Create Cloud SQL with HA
gcloud sql instances create mlflow-db \
  --database-version=POSTGRES_13 \
  --tier=db-custom-2-8192 \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --backup-start-time=02:00
```

### 2. Use Secrets Manager

Store credentials in Google Secret Manager:

```bash
# Create secret
echo -n "your-password" | gcloud secrets create postgres-password --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding postgres-password \
  --member="serviceAccount:your-sa@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Use External Secrets Operator to sync to Kubernetes.

### 3. Enable Connection Pooling

Add PgBouncer between app and database:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:latest
        # ... configuration
```

### 4. Set Up Monitoring

```bash
# Install Prometheus PostgreSQL Exporter
kubectl apply -f https://raw.githubusercontent.com/prometheus-community/postgres_exporter/master/kubernetes/deployment.yaml
```

### 5. Configure Backups

**For in-cluster PostgreSQL:**

```yaml
# Backup CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily
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
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: postgres-backup-pvc
          restartPolicy: OnFailure
```

**For Cloud SQL:** Backups are automatic!

---

## Complete Setup Checklist

- [ ] PostgreSQL deployed to GKE
- [ ] Database initialized with schema
- [ ] n8n credentials configured
- [ ] Test connection from n8n successful
- [ ] Test data inserted from n8n
- [ ] MLflow web app deployed
- [ ] Web UI accessible externally
- [ ] Articles from n8n visible in web UI
- [ ] CronJobs deployed for automation
- [ ] Backups configured
- [ ] Monitoring set up

---

## Quick Reference

### Service Names

| Service | Internal DNS | External Access |
|---------|-------------|-----------------|
| PostgreSQL | `postgres:5432` | Not exposed (internal only) |
| n8n | `n8n:5678` (your existing service) | LoadBalancer IP |
| Web UI | `news-triage-web:80` | LoadBalancer IP |
| MLflow | `mlflow:5000` | LoadBalancer IP |

### Common Commands

```bash
# Check PostgreSQL
kubectl get pods -l app=postgres
kubectl logs -l app=postgres

# Check web app
kubectl get pods -l app=news-triage-web
kubectl logs -l app=news-triage-web

# Check CronJobs
kubectl get cronjobs
kubectl get jobs --sort-by=.metadata.creationTimestamp

# Manual job execution
kubectl create job --from=cronjob/news-ingestion manual-ingest-1
kubectl create job --from=cronjob/embedding-generation manual-embed-1
kubectl create job --from=cronjob/model-training manual-train-1

# Database queries
POD=$(kubectl get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -- psql -U mlflow_user -d mlflow_db
```

---

## Next Steps

1. ✅ Complete this setup
2. ✅ Configure your n8n workflows to use PostgreSQL
3. ✅ Test article ingestion
4. ✅ Access web UI and start labeling
5. 🚀 Set up automated workflows (see DEPLOYMENT.md)

For detailed n8n workflow configuration, see [N8N_MIGRATION_GUIDE.md](N8N_MIGRATION_GUIDE.md)
