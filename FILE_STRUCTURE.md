# Concrete Agent - Complete File Structure

## Repository Root
```
concrete-agent/
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
├── README.md                    # Main documentation
├── IMPLEMENTATION_SUMMARY.md    # Implementation status
├── QUICKSTART.md                # Quick start guide
├── docker-compose.yml           # Docker composition
└── requirements.txt             # Root dependencies
```

## Backend Structure
```
backend/
├── Dockerfile                   # Backend container config
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   │
│   ├── core/                   # Core system modules
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── database.py         # Database connection
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── llm_service.py      # LLM integration (Anthropic/OpenAI)
│   │   ├── logging_config.py   # Logging setup
│   │   ├── orchestrator.py     # Agent orchestration
│   │   ├── prompt_loader.py    # Prompt management
│   │   └── utils.py            # Utility functions
│   │
│   ├── agents/                 # Modular agent system
│   │   ├── __init__.py
│   │   ├── base_agent.py       # Base agent with scientific method
│   │   │
│   │   ├── tzd_reader/         # TZD document parser
│   │   │   ├── __init__.py
│   │   │   ├── agent.py        # Agent implementation
│   │   │   ├── model.py        # Data models
│   │   │   ├── schema.py       # Pydantic schemas
│   │   │   ├── prompts/        # Agent-specific prompts
│   │   │   └── tests/
│   │   │       ├── __init__.py
│   │   │       └── test_tzd_reader.py
│   │   │
│   │   └── boq_parser/         # Bill of Quantities parser
│   │       ├── __init__.py
│   │       ├── agent.py        # Agent implementation
│   │       ├── prompts/        # Agent-specific prompts
│   │       └── tests/
│   │           └── __init__.py
│   │
│   ├── models/                 # Database ORM models
│   │   ├── __init__.py
│   │   ├── analysis_model.py   # Analysis records
│   │   ├── file_model.py       # File metadata
│   │   └── user_model.py       # User accounts
│   │
│   ├── schemas/                # Pydantic validation schemas
│   │   ├── __init__.py
│   │   ├── analysis_schema.py  # Analysis data schemas
│   │   ├── response_schema.py  # API response schemas
│   │   └── user_schema.py      # User data schemas
│   │
│   ├── routers/                # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── status_router.py    # System status endpoints
│   │   └── unified_router.py   # Main API endpoints
│   │
│   ├── services/               # Business logic services
│   │   ├── __init__.py
│   │   ├── normalization.py    # Czech text normalization
│   │   ├── registry.py         # Agent discovery & registration
│   │   ├── storage.py          # File storage service
│   │   └── validation.py       # Data validation service
│   │
│   ├── knowledgebase/          # Domain knowledge (ČSN, EN standards)
│   │   ├── mechanization.json  # Equipment data
│   │   ├── norms/
│   │   │   ├── csn_73_2400.json  # Czech concrete standard
│   │   │   └── en_206.json       # European concrete standard
│   │   ├── resources/
│   │   │   └── materials.json    # Material specifications
│   │   └── prices/
│   │       └── default_rates.json # Pricing data
│   │
│   ├── prompts/                # System-wide LLM prompts
│   │   ├── default_prompt.txt
│   │   ├── error_handling_prompt.txt
│   │   └── system_prompt.txt
│   │
│   └── tests/                  # Unit and integration tests
│       ├── __init__.py
│       ├── test_api_endpoints.py    # API tests (7 tests)
│       ├── test_normalization.py    # Normalization tests (6 tests)
│       └── test_registry.py         # Registry tests (4 tests)
```

## Frontend Structure
```
frontend/
├── Dockerfile                   # Frontend container config
├── package.json                 # Node dependencies
├── tsconfig.json               # TypeScript config
├── vite.config.ts              # Vite build config
├── index.html                  # HTML entry point
│
└── src/
    ├── main.tsx                # React entry point
    ├── App.tsx                 # Main app component
    ├── vite-env.d.ts           # Vite types
    │
    ├── pages/                  # Page components
    │   ├── HomePage.tsx        # Landing page
    │   ├── AnalysisPage.tsx    # Analysis interface
    │   └── ResultsPage.tsx     # Results display
    │
    ├── components/             # Reusable components
    │   └── ReasoningChain.tsx  # Scientific method display
    │
    ├── api/                    # API client
    │   └── client.ts           # Axios API client
    │
    ├── utils/                  # Utility functions
    │
    └── styles/                 # CSS styling
        ├── App.css
        └── index.css
```

## CI/CD & Infrastructure
```
.github/
└── workflows/
    ├── deploy-backend.yml      # Backend deployment to Render
    ├── deploy-frontend.yml     # Frontend deployment to Render
    ├── tests.yml              # Automated testing
    ├── render_purge.yml       # Cache management
    ├── qodo-scan.yml          # Code quality scanning
    ├── claude.yml             # Claude AI integration
    └── auto-fix.yml           # Automated fixes
```

## File Counts

| Category | Count |
|----------|-------|
| Backend Python files | 40+ |
| Frontend TypeScript files | 18 |
| Test files | 4 |
| Agent implementations | 2 |
| Workflow files | 7 |
| Knowledge base JSON files | 5 |
| Total lines of code | 3,000+ |

## Key Files

### Entry Points
- `backend/app/main.py` - FastAPI application
- `frontend/src/main.tsx` - React application

### Configuration
- `.env.example` - Environment template
- `backend/pyproject.toml` - Python project config
- `backend/requirements.txt` - Python dependencies
- `frontend/package.json` - Node dependencies

### Core Logic
- `backend/app/agents/base_agent.py` - Base agent with scientific method
- `backend/app/core/orchestrator.py` - Agent coordination
- `backend/app/services/registry.py` - Dynamic agent discovery

### Testing
- `backend/app/tests/test_*.py` - 17 tests total
- `pytest.ini` options in `pyproject.toml`

