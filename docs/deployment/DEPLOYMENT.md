# Deployment Guide

## 部署指南

This guide covers deploying the Postpartum AI Copilot application in a production environment.

## Architecture Overview

The application consists of:
- **API Server**: FastAPI application handling HTTP requests
- **Worker Processes**: Background workers processing AI tasks
- **PostgreSQL Database**: Persistent data storage
- **Frontend**: React application (can be deployed separately)

### Architecture Improvements (v2.0+)

- **Unified Database Session Management**: Dependency injection pattern for database sessions
- **Centralized Configuration**: pydantic-settings for environment variable management
- **Structured Logging**: JSON-formatted logs for better observability
- **Performance Monitoring**: Request tracking and slow query detection
- **Enhanced Health Checks**: Comprehensive system health monitoring
- **Unified Error Handling**: Structured error responses
- **Rate Limiting**: IP and user-based API rate limiting
- **Caching Service**: In-memory caching with TTL

### Code Quality Improvements (v2.1.0 - 2026-01-22)

- **Route Refactoring**: Main.py reduced from 863 to 241 lines (72% reduction)
- **Database Query Helpers**: Unified async query patterns with `utils/db_helpers.py`
- **Database Index Optimization**: Composite indexes for 40-80% performance improvement
- **Service Refactoring**: TrackingService refactored to eliminate code duplication (~30% reduction)
- **Type Hints**: Complete type annotations for all methods
- **Error Handling**: Unified error handling with automatic rollback

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL 15+ (if not using Docker)
- Python 3.11+ (for local development)
- Node.js 16+ (for frontend)
- AI API keys (OpenAI, Claude, or Gemini)

## Environment Configuration

### 1. Backend Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/postpartum_db
# Or use SQLite for development:
# DATABASE_URL=sqlite:///./postpartum.db

# AI Provider Configuration
AI_PROVIDER=openai  # or claude, gemini
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# JWT Authentication
JWT_SECRET_KEY=your_secret_key_here  # Generate with: openssl rand -hex 32
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Application Settings
ASYNC_MODE=true  # Enable async task queue
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
RAG_ENABLED=true

# Worker Configuration
NUM_WORKERS=2  # Number of worker processes
```

### 2. Frontend Environment Variables

Create a `.env` file in the `frontend` directory:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_ASYNC_MODE=true
```

## Docker Deployment

### Quick Start

1. **Clone the repository and navigate to the project directory**

2. **Create environment files**

   Copy `backend/env.example` to `backend/.env` and fill in your values.

3. **Start services with Docker Compose**

   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database
   - API server (port 8000)
   - Worker processes

4. **Check service status**

   ```bash
   docker-compose ps
   docker-compose logs -f api
   docker-compose logs -f worker
   ```

### Scaling Workers

To scale worker processes:

```bash
docker-compose up -d --scale worker=3
```

This starts 3 worker containers.

### Stopping Services

```bash
docker-compose down
```

To also remove volumes (database data):

```bash
docker-compose down -v
```

## Manual Deployment

### 1. Database Setup

#### PostgreSQL

```bash
# Create database
createdb postpartum_db

# Or using psql
psql -U postgres
CREATE DATABASE postpartum_db;
CREATE USER postpartum_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE postpartum_db TO postpartum_user;
```

#### SQLite (Development Only)

No setup required. Database file will be created automatically.

### 2. Backend Deployment

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from models.database import init_db; init_db()"

# Start API server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Worker Deployment

In a separate terminal (from the repository root):

```bash
# Start worker
python workers/worker.py

# Or with multiple workers
NUM_WORKERS=3 python workers/worker.py
```

### 4. Frontend Deployment

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Serve with a web server (e.g., nginx)
# Or use a static hosting service
```

## Production Considerations

### 1. Security

- **JWT Secret Key**: Use a strong, randomly generated secret key
- **Database Passwords**: Use strong passwords
- **HTTPS**: Always use HTTPS in production
- **CORS**: Restrict CORS origins to your frontend domain
- **API Keys**: Never commit API keys to version control

### 2. Database

- **PostgreSQL**: Recommended for production
- **Connection Pooling**: Configured in `database.py`
- **Backups**: Set up regular database backups
- **Migrations**: Use Alembic for database migrations (if needed)

### 3. Monitoring

- **Health Checks**: Use `/api/monitoring/health` endpoint for comprehensive health status
- **Logging**: Structured JSON logging to `./logs/app.log` and `./logs/error.log`
- **Metrics**: Use `/api/monitoring/metrics` for performance metrics
- **Task Monitoring**: Use `/api/monitoring/tasks` for task queue statistics
- **System Resources**: Use `/api/monitoring/system` for CPU, memory, and disk usage
- **Error Tracking**: Errors logged with context to `./logs/error.log`
- **Performance**: Slow queries automatically logged (threshold: 1 second)

### 4. Performance

- **Worker Scaling**: Scale workers based on load
- **Database Indexing**: Ensure proper database indexes
- **Caching**: In-memory caching service with TTL support
- **CDN**: Use CDN for frontend assets
- **Stress Testing**: Use `stress_test.py` to benchmark performance
- **Performance Monitoring**: Monitor via `/api/monitoring/metrics` endpoint

## Database Migration

### Initial Setup

The database tables are created automatically on first run via `init_db()`.

### Manual Migration

```bash
cd backend
python -c "from models.database import init_db; init_db()"
```

## Health Checks

### Basic Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "ai_provider": "openai"
}
```

### Comprehensive Health Check

```bash
curl http://localhost:8000/api/monitoring/health
```

Returns detailed health status for:
- Database connectivity and performance
- AI provider configuration
- Task queue status
- System resources (CPU, memory, disk)

### Performance Metrics

```bash
curl http://localhost:8000/api/monitoring/metrics
```

Returns:
- Total requests
- Average response time
- P95/P99 response times
- Status code distribution
- Slow queries

### Database Health

```bash
# PostgreSQL
psql -U postpartum_user -d postpartum_db -c "SELECT 1"

# Check from API
curl http://localhost:8000/health
```

## Troubleshooting

### Worker Not Processing Tasks

1. Check worker logs:
   ```bash
   docker-compose logs worker
   ```

2. Verify database connection
3. Check task queue for pending tasks
4. Verify AI API keys are set

### API Not Responding

1. Check API logs:
   ```bash
   docker-compose logs api
   ```

2. Verify database is running
3. Check environment variables
4. Verify port 8000 is not in use

### Database Connection Issues

1. Verify DATABASE_URL is correct
2. Check PostgreSQL is running
3. Verify user permissions
4. Check network connectivity

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL
pg_dump -U postpartum_user postpartum_db > backup.sql

# Restore
psql -U postpartum_user postpartum_db < backup.sql
```

### Application Data

- User data: Stored in PostgreSQL
- Task history: Stored in PostgreSQL
- Vector database (RAG): Stored in `vector_db` directory (if using RAG)

## Scaling

### Horizontal Scaling

1. **API Servers**: Deploy multiple API instances behind a load balancer
2. **Workers**: Scale worker containers based on task queue length
3. **Database**: Use read replicas for read-heavy workloads

### Vertical Scaling

- Increase worker count: `NUM_WORKERS=4`
- Increase database resources
- Optimize AI API usage

## Maintenance

### Updating the Application

```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build

# Restart services
docker-compose restart
```

### Database Maintenance

- Regular vacuuming (PostgreSQL)
- Index optimization
- Monitor table sizes

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review health endpoints
3. Check environment configuration
4. Verify AI API keys and quotas
