# Cargo Clash 

## Game Overview

Cargo Clash combines resource management, strategy, and fast-paced action in a persistent online world. Players manage fleets of vehicles, complete missions, trade in dynamic markets, form alliances, and engage in combat while building their cargo transportation empire.

### Core Features

- **Vehicle Management**: Own and upgrade trucks, ships, planes, and trains
- **Dynamic Missions**: Time-sensitive cargo delivery missions with varying difficulty
- **Market Trading**: Buy and sell goods in a fluctuating economy
- **Combat System**: PvP and PvE combat with strategic elements
- **Alliance System**: Form alliances and participate in faction wars
- **World Events**: Dynamic events that affect gameplay and economy
- **Real-time Updates**: Live game state via WebSocket connections

##  Technical Architecture

### Backend Stack
- **FastAPI**: High-performance Python web framework
- **PostgreSQL**: Primary database with SQLAlchemy ORM
- **Redis**: Caching and Celery message broker
- **Celery**: Asynchronous task processing
- **WebSockets**: Real-time communication
- **AWS Services**: Cognito, SQS, S3, CloudWatch

### Frontend Stack
- **React 18**: Modern UI framework with TypeScript
- **Material-UI**: Component library with custom theming
- **React Query**: Data fetching and caching
- **Socket.io**: Real-time WebSocket client
- **Framer Motion**: Smooth animations

### Infrastructure
- **AWS EKS**: Kubernetes orchestration
- **Docker**: Containerization
- **Application Load Balancer**: Traffic distribution
- **Auto Scaling**: Dynamic resource allocation
- **Monitoring**: CloudWatch metrics and logging

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- AWS CLI (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cargo-clash
   ```

2. **Start with Docker Compose**
   ```bash
   # Copy environment file
   cp env.example .env
   
   # Start all services
   docker-compose up -d
   ```

3. **Access the application

### Manual Setup

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://cargo_user:cargo_pass@localhost:5432/cargo_clash"
export REDIS_URL="redis://localhost:6379/0"

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

#### Celery Workers
```bash
cd backend
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://cargo_user:cargo_pass@localhost:5432/cargo_clash
ASYNC_DATABASE_URL=postgresql+asyncpg://cargo_user:cargo_pass@localhost:5432/cargo_clash

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
COGNITO_USER_POOL_ID=us-west-2_xxxxxxxxx
COGNITO_CLIENT_ID=your_client_id
SQS_QUEUE_URL=https://sqs.us-west-2.amazonaws.com/123456789012/cargo-clash-events

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
```

### AWS Services Setup

1. **AWS Cognito**: User authentication
2. **Amazon RDS**: PostgreSQL database
3. **Amazon SQS**: Message queuing
4. **Amazon S3**: File storage and backups
5. **CloudWatch**: Monitoring and metrics

## Deployment

### AWS EKS Deployment

1. **Create EKS cluster**
   ```bash
   eksctl create cluster --name cargo-clash --region us-west-2 --nodes 3
   ```

2. **Build and push Docker images**
   ```bash
   # Backend
   docker build -t cargo-clash/backend:latest ./backend
   docker tag cargo-clash/backend:latest <your-ecr-repo>/backend:latest
   docker push <your-ecr-repo>/backend:latest
   
   # Frontend
   docker build -t cargo-clash/frontend:latest ./frontend
   docker tag cargo-clash/frontend:latest <your-ecr-repo>/frontend:latest
   docker push <your-ecr-repo>/frontend:latest
   ```

3. **Deploy to Kubernetes**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/redis.yaml
   kubectl apply -f k8s/backend.yaml
   kubectl apply -f k8s/celery.yaml
   kubectl apply -f k8s/frontend.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

4. **Verify deployment**
   ```bash
   kubectl get pods -n cargo-clash
   kubectl get services -n cargo-clash
   ```

## Testing

### Load Testing
```bash
# Install locust
pip install locust

# Run load tests
locust -f scripts/load_test.py --host=http://localhost:8000
```

### Performance Testing
```bash
# Run performance validation
python scripts/performance_test.py
```

### Unit Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Performance Targets

##  Game Mechanics

### Vehicle Types
- **Trucks**: Fast, moderate capacity, vulnerable to attacks
- **Ships**: Slow, high capacity, good for bulk cargo
- **Planes**: Very fast, low capacity, expensive to operate
- **Trains**: Moderate speed, very high capacity, route-dependent

### Mission Types
- **Standard Delivery**: Transport cargo from A to B
- **Time-Critical**: Urgent deliveries with time limits
- **Dangerous Cargo**: High-risk, high-reward missions
- **Multi-Stop**: Complex routes with multiple destinations

### Combat System
- **PvP Combat**: Player vs Player battles
- **Pirate Encounters**: NPC threats in dangerous regions
- **Alliance Wars**: Large-scale faction conflicts
- **Defensive Measures**: Escorts, armor, and evasion

### Economic System
- **Dynamic Pricing**: Supply and demand affect prices
- **Market Events**: Random events impact economy
- **Trade Routes**: Profitable paths between locations
- **Resource Scarcity**: Limited supplies create opportunities

## Security

- **JWT Authentication**: Secure API access
- **AWS Cognito**: User management and authentication
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API abuse prevention
- **HTTPS/WSS**: Encrypted communications
- **Database Security**: Parameterized queries, connection pooling

## 📈 Monitoring

### Metrics Tracked
- **Response Times**: API and WebSocket latency
- **Throughput**: Requests per second
- **Error Rates**: Failed requests and exceptions
- **Resource Usage**: CPU, memory, database connections
- **Game Metrics**: Player actions, missions, combat events

### Dashboards
- **CloudWatch**: AWS infrastructure metrics
- **Application Metrics**: Custom game metrics
- **Database Performance**: Query performance and connections
- **Celery Monitoring**: Task processing via Flower

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check connection string in environment variables
   - Ensure database exists and user has permissions

2. **Redis Connection Issues**
   - Confirm Redis server is running
   - Check Redis URL configuration
   - Verify network connectivity

3. **WebSocket Connection Failures**
   - Check if backend WebSocket endpoint is accessible
   - Verify authentication token is valid
   - Ensure firewall allows WebSocket connections

4. **High Memory Usage**
   - Monitor Celery worker memory consumption
   - Check for memory leaks in long-running tasks
   - Consider reducing worker concurrency

### Logs
- **Application Logs**: `docker-compose logs backend`
- **Database Logs**: `docker-compose logs postgres`
- **Celery Logs**: `docker-compose logs celery-worker`

