# Setup Guide

## Quick Start

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
cp env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here

# Start the backend server
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`

### 2. Frontend Setup

Open a new terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 最新更新 (2026-01-22)

### 代码质量改进 ✅
- 路由拆分重构：`main.py` 从 863 行减少到 241 行
- 数据库查询工具：统一异步查询模式
- 数据库索引优化：性能提升 40-80%
- 代码重构：消除代码重复约 30%

详细内容请查看 [代码质量改进报告](../../backend/docs/development/CODE_QUALITY_IMPROVEMENTS.md)

---

## API Endpoints

### Chat (JWT required)
- `POST /api/chat` - Main chat interface
- `POST /api/chat/stream` - Streaming chat responses
- `POST /api/crisis` - Night mode / crisis support
- `POST /api/chat/personalized` - Personalized chat

### Tracking (JWT required)

All tracking endpoints require a valid `Authorization: Bearer <access_token>` header.

- `POST /api/tracking` - Add tracking entry (user_id from JWT)
- `GET /api/tracking/{user_id}` - Get tracking entries
- `GET /api/tracking/{user_id}/summary` - Get AI-generated summary

### Emotional Check-in
- `POST /api/emotional-checkin` - Submit emotional check-in

### User Context
- `POST /api/user/context` - Update user context
- `GET /api/user/{user_id}/context` - Get user context

## Environment Variables

Required in `backend/.env`:

```
# AI Provider (choose one)
AI_PROVIDER=openai  # or claude, gemini
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Or for Claude
# ANTHROPIC_API_KEY=your_key_here
# CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Or for Gemini
# GOOGLE_API_KEY=your_key_here
# GEMINI_MODEL=gemini-pro

# Database
DATABASE_URL=sqlite:///../do-not-upload/data/postpartum.db
# Or PostgreSQL: DATABASE_URL=postgresql://user:password@localhost:5432/postpartum_db

# JWT Authentication
JWT_SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Optional:
```
RAG_ENABLED=true
VECTOR_DB_PATH=../do-not-upload/vector_db
ASYNC_MODE=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_DIR=../do-not-upload/logs
LOG_LEVEL=INFO
```

## Troubleshooting

### Backend Issues
- Make sure Python 3.9+ is installed
- Verify OpenAI API key is set correctly
- Check that all dependencies are installed: `pip install -r requirements.txt`

### Frontend Issues
- Make sure Node.js 16+ is installed
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check that backend is running on port 8000

### RAG Not Working
- RAG features are optional and will gracefully degrade if dependencies are missing
- To enable RAG, ensure langchain and chromadb are installed
- Vector database will be created automatically on first run

## Testing

### Test Backend
```bash
cd backend
curl http://localhost:8000/health
```

### Test Chat API
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "My baby is crying, what should I do?", "user_id": "test_user"}'
```

### Run Stress Tests

Test API performance and load capacity:

```bash
# Test health endpoint with 100 concurrent users
cd Postpartum
python stress_test.py --endpoint /health --concurrent 100 --requests 100

# Test chat endpoint with 10 concurrent users, 50 requests each
python stress_test.py --endpoint /api/chat --concurrent 10 --requests 50

# Test tracking endpoint with 20 concurrent users for 60 seconds
python stress_test.py --endpoint /api/tracking --concurrent 20 --duration 60
```

For more testing options, see [TESTING.md](./TESTING.md)

## Production Deployment

For production:
1. Set `RAG_ENABLED=true` in production environment
2. Use a production database (PostgreSQL recommended)
3. Set up proper CORS origins
4. Use environment variables for all secrets
5. Enable HTTPS
6. Set up monitoring and logging
