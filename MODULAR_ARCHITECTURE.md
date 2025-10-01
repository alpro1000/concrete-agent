# Modular Architecture Guide

## Overview

This project now uses a fully modular, plug-and-play architecture where agents and routers can be added or removed without breaking the system.

## Key Principles

1. **Core Independence**: Core files never import specific agents
2. **Lazy Loading**: Agents are loaded only when needed
3. **Auto-Discovery**: Routers are automatically discovered from `app/routers/`
4. **Graceful Degradation**: System works even if agents are missing

## Architecture Components

### Core Files (Agent-Independent)

These files work without any specific agent:

- `app/main.py` - Application entry point with router auto-discovery
- `app/core/orchestrator.py` - Coordinates agents (lazy-loaded)
- `app/core/llm_service.py` - LLM integration (Claude, OpenAI, Perplexity)
- `app/core/prompt_loader.py` - Loads prompts from files
- `app/core/router_registry.py` - Auto-discovers and registers routers
- `app/core/app_factory.py` - Sets up core endpoints

### Agent Structure

Each agent is self-contained in `app/agents/{agent_name}/`:

```
app/agents/tzd_reader/
├── __init__.py
├── agent.py          # Main agent logic
├── security.py       # Security utilities (optional)
└── parsers.py        # Custom parsers (optional)
```

### Router Structure

Routers are auto-discovered from `app/routers/`:

```python
# app/routers/{agent_name}_router.py
from fastapi import APIRouter

# IMPORTANT: Must be named 'router' for auto-discovery
router = APIRouter(
    prefix="/api/v1/{agent_name}",
    tags=["Agent Name"],
)

@router.get("/health")
async def health():
    return {"status": "healthy"}
```

## Adding a New Agent

### Step 1: Create Agent Directory

```bash
mkdir -p app/agents/my_agent
```

### Step 2: Implement Agent

```python
# app/agents/my_agent/agent.py
class MyAgent:
    def __init__(self):
        self.name = "MyAgent"
    
    def analyze(self, file_path: str):
        # Your analysis logic here
        return {"result": "analysis"}

# Export main function
def analyze_files(files: list):
    agent = MyAgent()
    return agent.analyze(files[0])
```

### Step 3: Create Router (Optional)

```python
# app/routers/my_agent_router.py
from fastapi import APIRouter, UploadFile, File

router = APIRouter(
    prefix="/api/v1/my_agent",
    tags=["My Agent"],
)

@router.post("/analyze")
async def analyze(files: list[UploadFile] = File(...)):
    from app.agents.my_agent.agent import analyze_files
    # Implementation
    return {"success": True}
```

### Step 4: Register Agent in Orchestrator (Optional)

Edit `app/core/orchestrator.py` and add to `_get_agent()`:

```python
elif agent_name == 'my_agent':
    try:
        from agents.my_agent.agent import MyAgent
        agent = MyAgent()
    except ImportError as ie:
        logger.warning(f"My agent not available: {ie}")
```

### Step 5: Start Server

That's it! No changes to main.py needed. The router is auto-discovered!

```bash
python -m uvicorn app.main:app --reload
```

## Removing an Agent

1. Delete the agent folder: `rm -rf app/agents/{agent_name}`
2. Delete the router (if exists): `rm app/routers/{agent_name}_router.py`
3. Restart the server

The system will continue to work without that agent!

## Frontend Architecture

### Three-Panel Upload UI

The frontend provides three specialized upload panels:

1. **Technical Documents Panel**
   - Formats: PDF, DOCX, TXT
   - Max size: 10MB
   - Purpose: Technical specifications, TZD, project narratives

2. **Bills of Quantities Panel**
   - Formats: Excel (XLS, XLSX), XML, XC4, CSV
   - Max size: 15MB
   - Purpose: Work lists, estimates, quantities

3. **Drawings Panel**
   - Formats: PDF, DWG, DXF, JPG, PNG, Revit, ArchiCAD
   - Max size: 50MB
   - Purpose: Engineering drawings, architectural plans

### Multilingual Support

The UI supports three languages with proper diacritics:

- **Czech (cs)** - Default
- **English (en)** - Fallback
- **Russian (ru)**

Language files: `frontend/src/i18n/{cs,en,ru}.json`

To add a new language:

1. Create `frontend/src/i18n/{language_code}.json`
2. Add to `frontend/src/i18n/index.ts`:

```typescript
import newLang from './newlang.json';

const resources = {
  // ...existing languages
  newlang: { translation: newLang },
};

export const languageOptions: LanguageOption[] = [
  // ...existing options
  { code: 'newlang', name: 'Language Name', flag: '🏳️' },
];
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_concrete_agent.py -v

# Run with coverage
pytest tests/ --cov=app
```

### Test Structure

Tests are now agent-independent:

- `test_concrete_agent.py` - Tests core modules only
- `test_integration.py` - Tests orchestrator file detection and lazy loading
- `test_llm_service.py` - Tests LLM service
- `test_upload_endpoints.py` - Tests router auto-discovery

## Configuration

### Backend Configuration

Key environment variables:

```bash
# LLM API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
PERPLEXITY_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Server
PORT=8000
```

### Frontend Configuration

`frontend/vite.config.ts`:

```typescript
export default defineConfig({
  preview: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['stav-agent.onrender.com', 'localhost', '127.0.0.1'],
  },
  // ...
});
```

## Deployment

### Backend Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend Deployment

```bash
# Build
cd frontend
npm run build

# Preview
npm run preview

# Serve dist/ folder with any static server
```

## Best Practices

1. **Keep core files agent-independent**
   - Don't import specific agents in core files
   - Use lazy loading in orchestrator

2. **Use proper error handling**
   - Agents can be unavailable - handle gracefully
   - Log warnings, not errors, for missing optional agents

3. **Follow naming conventions**
   - Routers must be named `router` in their file
   - Agent folders should match their purpose

4. **Document your agents**
   - Add README.md in each agent folder
   - Document API endpoints in router

5. **Test agent independence**
   - Tests should work even if agents are removed
   - Test core functionality separately from agents

## Troubleshooting

### Router not discovered

Check:
1. File is in `app/routers/` directory
2. Router variable is named `router`
3. No syntax errors in router file

### Agent not loading

Check:
1. Agent is in `app/agents/{agent_name}/`
2. Agent is registered in orchestrator's `_get_agent()`
3. No import errors in agent code

### Frontend language not working

Check:
1. Translation file exists in `frontend/src/i18n/`
2. Language is registered in `index.ts`
3. Translation keys match usage in components

## Support

For issues or questions:
- Check logs in `logs/` directory
- Enable debug mode: `LOG_LEVEL=DEBUG`
- Review test output: `pytest -v`
