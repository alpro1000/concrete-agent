# Quick Start Guide - Concrete Agent

## Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL (optional, SQLite works for development)

## Option 1: Quick Start with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/alpro1000/concrete-agent.git
cd concrete-agent

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys (optional for testing without LLM)

# Start everything with Docker
docker-compose up -d

# Access the application
# Backend API: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## Option 2: Manual Setup

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment (copy from parent directory)
cp ../.env.example .env
# Edit .env with your configuration

# Run the backend server
uvicorn app.main:app --reload

# Backend will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

### Frontend Setup

```bash
# Open a new terminal
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Edit .env if needed (default should work)

# Run the development server
npm run dev

# Frontend will be available at http://localhost:3000
```

### Run Tests

```bash
# Backend tests
cd backend
pytest -v

# All tests should pass (17 tests)
```

## First Steps

1. **Check System Status**
   - Open browser to http://localhost:8000/docs
   - Try the `/api/status` endpoint
   - Verify agents are discovered

2. **Test an Agent**
   - Use the `/api/agents/execute` endpoint
   - Agent name: `tzd_reader` or `boq_parser`
   - Input data: `{"document": "Your text here"}`

3. **Explore the Frontend**
   - Open http://localhost:3000
   - See system status on home page
   - Try the analysis page to upload documents

## Sample API Request

```bash
# List available agents
curl http://localhost:8000/api/agents/agents

# Execute TZD Reader agent
curl -X POST http://localhost:8000/api/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "tzd_reader",
    "input_data": {
      "document": "TECHNICKÁ ZADÁVACÍ DOKUMENTACE\nBeton C25/30"
    }
  }'
```

## Configuration

### Backend (.env)
```env
# LLM API Keys (optional for testing)
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Database (default uses SQLite)
DATABASE_URL=sqlite:///./concrete_agent.db

# Server
API_PORT=8000
DEBUG=true
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
```

## Development Workflow

### Adding a New Agent

1. Create directory: `backend/app/agents/my_agent/`
2. Create `agent.py` with your agent class
3. Create `prompts/system.txt` with LLM prompt
4. Agent will be automatically discovered on restart!

```python
from app.agents.base_agent import BaseAgent, AgentResult

class MyAgent(BaseAgent):
    name = "my_agent"
    description = "My custom agent"
    version = "1.0.0"
    
    async def execute(self, input_data):
        # Your implementation
        pass
```

### Running in Production

```bash
# Build frontend
cd frontend
npm run build

# Run backend with production settings
cd backend
export DEBUG=false
export ENVIRONMENT=production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

### "No LLM clients available" warning
- This is normal if API keys are not configured
- The system will work for non-LLM features
- Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env to enable LLM features

### Database connection failed
- Using SQLite by default (no setup needed)
- For PostgreSQL, ensure connection string is correct in DATABASE_URL

### Port already in use
- Change API_PORT in backend/.env
- Change port in frontend/vite.config.ts
- Update VITE_API_URL in frontend/.env

## Next Steps

1. Read the [README.md](README.md) for full documentation
2. Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
3. Explore API documentation at http://localhost:8000/docs
4. Review agent code in `backend/app/agents/`
5. Customize knowledge base in `backend/app/knowledgebase/`

## Support

For issues or questions:
1. Check the documentation in README.md
2. Review API docs at /docs endpoint
3. Check logs in backend/logs/app.log
4. Open an issue on GitHub

## Quick Commands Reference

```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# Start frontend
cd frontend && npm run dev

# Run tests
cd backend && pytest

# Check code coverage
cd backend && pytest --cov=app --cov-report=html

# Build for production
cd frontend && npm run build
cd backend && python -m build

# Docker
docker-compose up -d          # Start
docker-compose down           # Stop
docker-compose logs -f        # View logs
```

Happy coding! 🚀
