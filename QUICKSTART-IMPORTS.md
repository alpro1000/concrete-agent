# Quick Reference - Import Fix

## TL;DR - What Changed

**Before (❌ DEPRECATED):**
```bash
cd backend
uvicorn app.main:app
```

**After (✅ CORRECT):**
```bash
# Always from project root
cd concrete-agent
uvicorn backend.app.main:app
```

## Commands Quick Reference

### Local Development
```bash
# From project root
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development
```bash
docker-compose up -d
```

### Run Tests
```bash
pytest backend/tests/test_imports.py backend/app/tests/ -v
```

### Render Deployment
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory:** `/` (empty or project root)

## Import Pattern

**Always use full package paths:**

```python
# ✅ CORRECT
from backend.app.core import settings
from backend.app.services import agent_registry
from backend.app.models import User, Analysis

# ❌ WRONG (old pattern)
from app.core import settings
from app.services import agent_registry
```

## Project Structure

```
concrete-agent/              ← Run commands from here!
├── backend/
│   ├── __init__.py         ← Makes 'backend' a package
│   └── app/
│       ├── main.py         ← No sys.path hacks
│       ├── core/
│       ├── models/
│       └── services/
├── Dockerfile.backend      ← Production Dockerfile
├── requirements.txt
└── DEPLOYMENT.md           ← Full guide
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `No module named 'backend'` | Run from project root, not backend/ |
| `No module named 'app'` | Update imports to use `backend.app.*` |
| Docker build fails | Use `docker build -f Dockerfile.backend .` |
| Tests fail | Run from project root: `pytest backend/...` |

## Key Files

- `DEPLOYMENT.md` - Complete deployment guide
- `backend/tests/test_imports.py` - 9 import validation tests
- `Dockerfile.backend` - Production Docker config
- `.github/workflows/deploy-backend.yml` - CI/CD pipeline

## Quick Health Check

```bash
# Start the app
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# In another terminal
curl http://localhost:8000/health
curl http://localhost:8000/status
```

Expected:
```json
{
  "status": "healthy",
  "agents": ["boq_parser", "base_agent", "tzd_reader"],
  "database": "connected"
}
```

---

**For full details, see [DEPLOYMENT.md](DEPLOYMENT.md)**
