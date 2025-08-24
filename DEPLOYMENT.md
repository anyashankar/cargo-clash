# Cargo Clash Deployment Guide

This guide provides detailed instructions for deploying Cargo Clash to AWS EKS with production-grade configuration.

## Prerequisites

### Required Tools
- AWS CLI v2
- kubectl
- eksctl
- Docker

## Infrastructure Setup

### 1. Create EKS Cluster

```bash
# Create EKS cluster with managed node groups
eksctl create cluster \
  --name cargo-clash \
  --region us-west-2 \
  --version 1.24 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \
  --enable-ssm

# Verify cluster creation
kubectl get nodes
```

### 2. Install AWS Load Balancer Controller

```bash
# Create IAM OIDC provider
eksctl utils associate-iam-oidc-provider \
  --region us-west-2 \
  --cluster cargo-clash \
  --approve

# Create IAM service account
eksctl create iamserviceaccount \
  --cluster=cargo-clash \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess \
  --override-existing-serviceaccounts \
  --approve

# Install AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller/crds?ref=master"

helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=cargo-clash \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

### 3. Set Up Amazon RDS

```bash
# Create RDS subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name cargo-clash-subnet-group \
  --db-subnet-group-description "Subnet group for Cargo Clash RDS" \
  --subnet-ids subnet-12345678 subnet-87654321

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier cargo-clash-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username cargo_user \
  --master-user-password "SecurePassword123!" \
  --allocated-storage 20 \
  --db-name cargo_clash \
  --db-subnet-group-name cargo-clash-subnet-group \
  --vpc-security-group-ids sg-12345678 \
  --backup-retention-period 7 \
  --multi-az \
  --storage-encrypted
```

### 4. Configure AWS Services

#### SQS Queue
```bash
# Create SQS queue for game events
aws sqs create-queue \
  --queue-name cargo-clash-events \
  --attributes VisibilityTimeoutSeconds=300,MessageRetentionPeriod=1209600
```

#### S3 Bucket
```bash
# Create S3 bucket for game assets and logs
aws s3 mb s3://cargo-clash-assets-us-west-2
aws s3 mb s3://cargo-clash-logs-us-west-2

# Enable versioning and encryption
aws s3api put-bucket-versioning \
  --bucket cargo-clash-assets-us-west-2 \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket cargo-clash-assets-us-west-2 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

#### Cognito User Pool
```bash
# Create Cognito User Pool
aws cognito-idp create-user-pool \
  --pool-name cargo-clash-users \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": false
    }
  }' \
  --auto-verified-attributes email

# Create User Pool Client
aws cognito-idp create-user-pool-client \
  --user-pool-id us-west-2_XXXXXXXXX \
  --client-name cargo-clash-client \
  --generate-secret
```

## Container Registry Setup

### 1. Create ECR Repositories

```bash
# Create repositories for backend and frontend
aws ecr create-repository --repository-name cargo-clash/backend
aws ecr create-repository --repository-name cargo-clash/frontend

# Get login token
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com
```

### 2. Build and Push Images

```bash
# Build backend image
cd backend
docker build -t cargo-clash/backend:latest .
docker tag cargo-clash/backend:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/backend:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/backend:latest

# Build frontend image
cd ../frontend
docker build -t cargo-clash/frontend:latest .
docker tag cargo-clash/frontend:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/frontend:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/frontend:latest
```

## Kubernetes Deployment

### 1. Update Configuration

Update the Kubernetes manifests with your specific values:

```bash
# Update k8s/configmap.yaml with your configuration
# Update k8s/secrets.yaml with base64 encoded secrets
# Update k8s/ingress.yaml with your domain and certificate ARN
```

### 2. Create Secrets

```bash
# Create secrets with actual values
kubectl create secret generic cargo-clash-secrets \
  --from-literal=SECRET_KEY="your-super-secret-key" \
  --from-literal=POSTGRES_PASSWORD="SecurePassword123!" \
  --from-literal=AWS_ACCESS_KEY_ID="your-access-key" \
  --from-literal=AWS_SECRET_ACCESS_KEY="your-secret-key" \
  --from-literal=COGNITO_CLIENT_SECRET="your-cognito-secret" \
  --namespace=cargo-clash
```

### 3. Deploy Application

```bash
# Apply all Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n cargo-clash --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n cargo-clash --timeout=300s

# Deploy application services
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/celery.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n cargo-clash

# Check services
kubectl get services -n cargo-clash

# Check ingress
kubectl get ingress -n cargo-clash

# View logs
kubectl logs -f deployment/backend -n cargo-clash
```

## Database Migration

### 1. Run Initial Migration

```bash
# Create a job to run database migrations
kubectl create job --from=cronjob/migrate-db migrate-db-initial -n cargo-clash

# Or run manually in a pod
kubectl run migrate-db --image=<account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/backend:latest \
  --rm -it --restart=Never \
  --env="DATABASE_URL=postgresql://cargo_user:SecurePassword123!@postgres-service:5432/cargo_clash" \
  -- alembic upgrade head
```

### 2. Seed Initial Data

```bash
# Create initial game data (locations, market prices, etc.)
kubectl run seed-data --image=<account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/backend:latest \
  --rm -it --restart=Never \
  --env="DATABASE_URL=postgresql://cargo_user:SecurePassword123!@postgres-service:5432/cargo_clash" \
  -- python -c "
from app.database import SessionLocal
from app.models import Location, MarketPrice, CargoType
import random

db = SessionLocal()

# Create sample locations
locations = [
    Location(name='New Harbor', location_type='port', x_coordinate=100, y_coordinate=200, region='North'),
    Location(name='Steel City', location_type='industrial', x_coordinate=300, y_coordinate=150, region='Central'),
    Location(name='Trade Hub', location_type='commercial', x_coordinate=200, y_coordinate=300, region='South'),
]

for location in locations:
    db.add(location)

db.commit()
print('Sample data created successfully!')
"
```

## SSL Certificate Setup

### 1. Request Certificate from ACM

```bash
# Request SSL certificate
aws acm request-certificate \
  --domain-name cargo-clash.yourdomain.com \
  --validation-method DNS \
  --region us-west-2

# Note the certificate ARN and update ingress.yaml
```

### 2. Configure DNS

```bash
# Create Route 53 hosted zone (if needed)
aws route53 create-hosted-zone \
  --name yourdomain.com \
  --caller-reference $(date +%s)

# Create CNAME record for certificate validation
# (Follow ACM console instructions)

# Create A record pointing to ALB
# (Get ALB DNS name from ingress)
```

## Monitoring Setup

### 1. CloudWatch Container Insights

```bash
# Install CloudWatch agent
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-daemonset.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/fluentd/fluentd-daemonset-cloudwatch.yaml
```

### 2. Prometheus and Grafana (Optional)

```bash
# Install Prometheus using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

## Backup and Disaster Recovery

### 1. Database Backups

```bash
# Enable automated backups in RDS (already configured above)
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier cargo-clash-db \
  --db-snapshot-identifier cargo-clash-db-snapshot-$(date +%Y%m%d)
```

### 2. Application Data Backup

```bash
# Create backup job for application data
kubectl create job backup-app-data --image=<account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/backend:latest \
  --env="DATABASE_URL=postgresql://cargo_user:SecurePassword123!@postgres-service:5432/cargo_clash" \
  --env="AWS_ACCESS_KEY_ID=your-key" \
  --env="AWS_SECRET_ACCESS_KEY=your-secret" \
  -- python -c "
from app.tasks.maintenance_tasks import backup_player_data
import asyncio
asyncio.run(backup_player_data())
"
```

## Scaling Configuration

### 1. Horizontal Pod Autoscaler

```bash
# HPA is already configured in the manifests
# Verify HPA status
kubectl get hpa -n cargo-clash
```

### 2. Cluster Autoscaler

```bash
# Install cluster autoscaler
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# Edit deployment to add cluster name
kubectl -n kube-system edit deployment.apps/cluster-autoscaler
# Add --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/cargo-clash
```

## Security Hardening

### 1. Network Policies

```bash
# Apply network policies to restrict pod-to-pod communication
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cargo-clash-network-policy
  namespace: cargo-clash
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
EOF
```

### 2. Pod Security Standards

```bash
# Apply pod security standards
kubectl label namespace cargo-clash pod-security.kubernetes.io/enforce=restricted
kubectl label namespace cargo-clash pod-security.kubernetes.io/audit=restricted
kubectl label namespace cargo-clash pod-security.kubernetes.io/warn=restricted
```

## Performance Optimization

### 1. Resource Limits and Requests

Ensure all pods have appropriate resource limits and requests set in the manifests.

### 2. Database Connection Pooling

Configure connection pooling in the application:

```python
# In backend/app/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending state**
   ```bash
   kubectl describe pod <pod-name> -n cargo-clash
   # Check for resource constraints or node selector issues
   ```

2. **Database connection issues**
   ```bash
   kubectl exec -it deployment/backend -n cargo-clash -- python -c "
   from app.database import engine
   with engine.connect() as conn:
       result = conn.execute('SELECT 1')
       print('Database connection successful')
   "
   ```

3. **Load balancer not accessible**
   ```bash
   kubectl get ingress -n cargo-clash
   kubectl describe ingress cargo-clash-ingress -n cargo-clash
   ```

### Useful Commands

```bash
# View all resources
kubectl get all -n cargo-clash

# Check resource usage
kubectl top pods -n cargo-clash
kubectl top nodes

# View events
kubectl get events -n cargo-clash --sort-by=.metadata.creationTimestamp

# Port forward for debugging
kubectl port-forward service/backend-service 8000:8000 -n cargo-clash
```

## Maintenance

### Regular Tasks

1. **Update container images**
2. **Monitor resource usage**
3. **Review logs for errors**
4. **Check backup status**
5. **Update Kubernetes cluster**
6. **Review security patches**

### Automated Maintenance

Set up automated tasks using Kubernetes CronJobs:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-backup
  namespace: cargo-clash
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: <account-id>.dkr.ecr.us-west-2.amazonaws.com/cargo-clash/backend:latest
            command: ["python", "-c", "from app.tasks.maintenance_tasks import backup_player_data; import asyncio; asyncio.run(backup_player_data())"]
          restartPolicy: OnFailure
```

This deployment guide provides a comprehensive approach to deploying Cargo Clash in a production environment with high availability, security, and scalability considerations.
