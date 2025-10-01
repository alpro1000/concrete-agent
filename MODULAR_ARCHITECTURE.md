# Modular Architecture Guide - Beads System

## Overview

This project uses a **beads system** architecture - a fully modular, plug-and-play architecture where agents are automatically discovered and loaded dynamically. No hardcoded agent references in the core!

## Key Principles

1. **Core Independence**: Core files never import specific agents directly
2. **Dynamic Discovery**: Agents are automatically discovered from `app/agents/` directory
3. **BaseAgent Interface**: All agents inherit from `BaseAgent` with a standard interface
4. **Auto-Loading**: The orchestrator automatically finds and loads available agents
5. **Graceful Degradation**: System works even if agents are missing

## Architecture Components

### Core Files (Agent-Independent)

These files work without any specific agent:

- `app/main.py` - Application entry point with router auto-discovery
- `app/core/orchestrator.py` - Coordinates agents with dynamic discovery
- `app/core/llm_service.py` - LLM integration (Claude, OpenAI, Perplexity)
- `app/core/prompt_loader.py` - Loads prompts from files
- `app/core/router_registry.py` - Auto-discovers and registers routers
- `app/core/app_factory.py` - Sets up core endpoints

### BaseAgent Interface

All agents **must** inherit from `BaseAgent` and implement:

```python
# app/agents/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAgent(ABC):
    # Agent identifier - must be overridden
    name: str = "base"
    
    # List of supported file types - must be overridden
    supported_types: List[str] = []
    
    @abstractmethod
    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """Analyze a file and return results"""
        pass
```

### Agent Structure

Each agent is self-contained in `app/agents/{agent_name}/`:

```
app/agents/
├── base.py            # BaseAgent interface
└── tzd_reader/        # Example agent
    ├── __init__.py
    ├── agent.py       # Main agent logic (contains agent class)
    └── security.py    # Security utilities (optional)
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

### Step 2: Implement Agent (Inherit from BaseAgent)

```python
# app/agents/my_agent/agent.py
from app.agents.base import BaseAgent
from typing import Dict, Any

class MyAgent(BaseAgent):
    """My custom agent for analyzing specific document types"""
    
    # Required: Define agent name
    name = "my_agent"
    
    # Required: Define supported file/document types
    supported_types = ["pdf", "docx", "my_custom_type"]
    
    def __init__(self):
        """Initialize your agent"""
        super().__init__()
        # Your initialization code here
    
    # Required: Implement analyze method
    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a file and return structured results
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Your analysis logic here
        return {
            "success": True,
            "result": "analysis complete"
        }
```

**Important:** The agent class will be automatically discovered! Just make sure:
- It has `name` and `supported_types` attributes
- It implements the `analyze(file_path)` method
- It's defined in `app/agents/{agent_name}/agent.py`

### Step 3: Create Router (Optional)

```python
# app/routers/my_agent_router.py
from fastapi import APIRouter, UploadFile, File
from app.core.orchestrator import get_orchestrator_service

# IMPORTANT: Must be named 'router' for auto-discovery
router = APIRouter(
    prefix="/api/v1/my_agent",
    tags=["My Agent"],
)

@router.post("/analyze")
async def analyze(files: list[UploadFile] = File(...)):
    orchestrator = get_orchestrator_service()
    # The orchestrator will automatically select the right agent
    result = await orchestrator.process_file(files[0].filename)
    return {"success": True, "result": result}
```

### Step 4: Start Server

That's it! **No changes needed** to orchestrator or core files. The agent is **automatically discovered**!

```bash
python -m uvicorn app.main:app --reload
```

The orchestrator will:
1. Scan `app/agents/` directory
2. Find your agent's `agent.py` file
3. Import and instantiate your agent class
4. Make it available for file processing

## How Agent Discovery Works

The orchestrator automatically discovers agents using the `discover_agents()` function:

1. **Scans** `app/agents/` directory for subdirectories
2. **Looks** for `agent.py` file in each subdirectory
3. **Imports** the module and searches for classes with:
   - `name` attribute
   - `supported_types` attribute
   - `analyze` method
4. **Instantiates** the agent and caches it
5. **Matches** files to agents based on `supported_types`

### Agent Selection Process

When a file needs to be analyzed:

1. Orchestrator detects file type (e.g., "pdf", "technical_assignment")
2. Calls `get_agent_for_type(file_type)` which:
   - Ensures agents are discovered (lazy loading)
   - Finds first agent that supports the file type
   - Returns the agent instance
3. Calls `agent.analyze(file_path)` on selected agent

### Example Flow

```python
# User uploads technical_assignment.pdf
file_type = orchestrator.detect_file_type("technical_assignment.pdf")
# Returns: "technical_assignment"

agent = orchestrator.get_agent_for_type("technical_assignment")
# Discovers agents if not already done
# Finds TZDReaderAgent because it has "technical_assignment" in supported_types

result = await agent.analyze("technical_assignment.pdf")
# Agent processes the file and returns results
```

## Removing an Agent

1. Delete the agent folder: `rm -rf app/agents/{agent_name}`
2. Delete the router (if exists): `rm app/routers/{agent_name}_router.py`
3. Restart the server

**The system will continue to work!** The orchestrator will simply not find that agent during discovery.

## Benefits of the Beads System

1. **Zero Coupling**: Core doesn't know about specific agents
2. **Plug & Play**: Drop in a new agent folder and it's discovered
3. **Hot-Swappable**: Agents can be added/removed without code changes
4. **Type-Safe**: BaseAgent enforces a consistent interface
5. **Maintainable**: Each agent is isolated and self-contained
6. **Testable**: Agents can be tested independently

## Example: TZD Reader Agent

```python
# app/agents/tzd_reader/agent.py
class TZDReaderAgent:
    name = "tzd_reader"
    supported_types = [
        "technical_assignment",
        "technical_document", 
        "pdf",
        "docx",
        "doc",
        "txt"
    ]
    
    async def analyze(self, file_path: str) -> Dict[str, Any]:
        # Analyzes technical assignment documents
        result = tzd_reader(files=[file_path], engine="auto")
        return result
```

This agent is **automatically discovered** and used when:
- A file is detected as "technical_assignment"
- A PDF/DOCX needs TZD analysis
- No manual registration needed!

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
1. Agent is in `app/agents/{agent_name}/` directory
2. Agent class has `name`, `supported_types` attributes
3. Agent class implements `analyze(file_path)` method
4. No import errors in agent code
5. Check logs for discovery errors: `grep "Discovered agent" logs/*.log`

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
