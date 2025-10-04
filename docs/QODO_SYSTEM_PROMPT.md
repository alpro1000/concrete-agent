# 🧠 QODO SYSTEM PROMPT — "Rebuild Concrete Agent / Stav Agent v1.5-CZ"

> **Note:** This document serves as a specification and system prompt for AI-assisted development tools (e.g., Qodo AI, Claude Sonnet 4.5, GPT-5 mini). It describes the ideal architecture and requirements for the Stav Agent (Concrete Agent) service.

## 🎯 Objective

Fully rebuild or maintain the Stav Agent (Concrete Agent) service in the repository `https://github.com/alpro1000/concrete-agent.git` according to the architecture, specification, and logic described below.

The service must be compatible with Render.com, fully functional, with synchronized frontend/backend variables, Czech interface, and using modern LLMs (Claude Sonnet 4.5 + GPT-5 mini backup).

---

## 🧩 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | Python 3.11 + FastAPI | ≥0.115 |
| Frontend | React 18 + TypeScript + Vite | Latest |
| LLM Provider | Anthropic Claude Sonnet 4.5 | 2025 |
| Backup LLM | OpenAI GPT-5 mini | 2025 |
| Deploy | Render.com | Dockerized |
| Lang | 🇨🇿 Czech UI (cs.json) | ✅ |
| Data exchange | JSON / REST API (UTF-8, snake_case) | ✅ |

---

## ⚙️ General Requirements

### Project Structure

```
/backend       # FastAPI application
/frontend      # React + TypeScript + Vite
/knowledgebase # Standards, norms, materials DB
/prompts       # LLM prompts (txt/json)
/storage       # Runtime file storage
```

### Core Principles

1. **Clean Architecture**
   - All modules mutually consistent
   - Variables match in naming (camel_case → snake_case)
   - All API endpoints documented at `/docs`
   - LLM calls centralized in `app/core/llm_service.py`

2. **Multi-Agent Architecture**
   - Each agent is a separate module with `analyze()` or `estimate()` function
   - Orchestrator links agents in pipeline
   - Modular, plug-and-play design (see `docs/architecture/stav-agent-modular-arch.md`)

3. **Frontend Integration**
   - React reads `/api/v1/*` directly via axios
   - Interface fully Czech (localization `cs.json`) ✅
   - Features: chat, file upload, analysis history

4. **Variable Synchronization**
   - `user_id`, `analysis_id`, `result`, `resources`, `tov` identically named in BE/FE
   - Errors (422/404/500) handled uniformly

5. **Scientific Design Method**
   - Each module documented with docstrings (ENG + CZ)
   - Logic and variables tested with unit tests (pytest)
   - "Prompt as Function" principle — agent prompts stored in `/prompts/*.txt`

---

## 🧠 Agent Architecture (Required Agents)

| # | Agent Name | Description | Status |
|---|-----------|-------------|--------|
| 1 | **TZDReaderAgent** | Reads technical specifications (PDF/DOCX) | ✅ Implemented |
| 2 | **BOQParserAgent** | Parses bill of quantities (XLS/XLSX) | 🔶 Planned |
| 3 | **DrawingParserAgent** | Reads drawings and extracts materials | 🔶 Planned |
| 4 | **ResourceEstimatorAgent** | Estimates materials, labor, machinery | 🔶 Planned |
| 5 | **SiteForemanAgent** | Plans schedule and TOV | 🔶 Planned |
| 6 | **KnowledgeBaseAgent** | Provides ČSN, GOST, URS norms | 🔶 Planned |
| 7 | **ExportAgent** | Generates PDF/DOCX/XLSX outputs | 🔶 Planned |
| 8 | **UserManagerAgent** | User management, history, login | 🔶 Planned |
| 9 | **ChatAgent** | Conversational LLM interface | 🔶 Optional |
| 10 | **OrchestratorAgent** | Controls sequence and orchestration | ✅ Partial |

---

## 🧩 LLM and Prompt Integration

### Centralized Service

```python
# app/core/llm_service.py
LLM_PROVIDER = "anthropic"
LLM_MODEL = "claude-sonnet-4.5"  # or "claude-sonnet-4-20250514"
BACKUP_PROVIDER = "openai"
BACKUP_MODEL = "gpt-5-mini"  # or "gpt-4o-mini"
```

**Status:** ✅ Implemented with proper fallback mechanism

### Prompt Files

```
/prompts/
  ├── tzd.txt          # ✅ Exists as tzd_prompt.json
  ├── boq.txt          # 🔶 Planned
  ├── drawing.txt      # 🔶 Planned
  ├── resource.txt     # 🔶 Planned
  ├── site.txt         # 🔶 Planned
  ├── export.txt       # 🔶 Planned
  └── chat.txt         # 🔶 Planned
```

**Status:** ✅ Prompt loading infrastructure exists

---

## 🧾 Knowledge Base

### Structure

```
/knowledgebase/
  ├── standards/
  │   ├── csn.json           # ČSN construction standards
  │   └── urs_kros_codes.json # KROS, RTS budget codes
  ├── materials/
  │   └── base.json          # Construction materials
  └── labor/
      └── norms.json         # Labor norms per ČSN and ÚRS
```

### API Access

- `GET /api/v1/knowledge/<category>` returns JSON for agent queries
- **Status:** 🔶 Planned

---

## 🧩 Frontend (React + Vite + TypeScript)

### Key Files

```
/frontend/src/
  ├── locales/cs.json        # ✅ Czech translation
  ├── pages/
  │   ├── Home.tsx          # ✅ Main page (upload files)
  │   └── History.tsx       # ✅ Analysis history (AccountPage)
  ├── components/
  │   └── ChatBox.tsx       # 🔶 Chat with agent
  └── api/
      └── api.ts            # ✅ API client (client.ts)
```

### Configuration

- **baseURL:** `https://concrete-agent.onrender.com`
- **Localization:** Czech (cs.json) ✅ Implemented
- **UI:** Clean, concise, bilingual ready (CZ, EN)

### Localization Keys

```json
{
  "app.title": "Stav Agent",
  "home.upload": "Nahrát",
  "history.empty": "Zatím žádné analýzy...",
  "chat.agent": "Chat"
}
```

**Status:** ✅ Fully implemented

---

## 🧪 Testing and Quality Control

### Test Structure

```
/backend/tests/
  ├── test_agents.py         # 🔶 Agent tests
  ├── test_routes.py         # 🔶 Route tests
  └── test_upload_contract.py # ✅ Upload contract tests (8/8 passing)
```

### Code Quality

- ✅ Black formatter (configured)
- ✅ Type hints with mypy
- 🔶 Pre-commit hooks via GitHub Actions

---

## 🚀 Deployment on Render

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend ./backend
RUN pip install -r backend/requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
```

**Status:** ✅ Dockerfile exists (port configurable via env)

### Configuration

1. ✅ Port 10000 configurable via `PORT` env variable
2. ✅ Frontend builds and deploys separately (`npm run build`)
3. ✅ CORS configured for production origins

---

## 🧠 Execution Logic

### Implementation Steps

1. ✅ ~~Clean old code~~ **Current code is functional - maintain existing structure**
2. ✅ Project structure follows specification
3. ✅ TZD Reader agent implemented in `/app/agents/tzd_reader/`
4. ✅ Prompts configuration in `/app/prompts/`
5. ✅ LLM Service configured (Claude Sonnet 4.5 + GPT backup)
6. ✅ React TypeScript frontend with Czech UI
7. ✅ FE/BE variable synchronization
8. 🔶 Complete pipeline: upload → analyze → export → chat
9. ✅ Render-ready Dockerfile and .env.template
10. ✅ Repository maintained at `https://github.com/alpro1000/concrete-agent.git`

---

## ✅ Success Criteria

| Check | Description | Status |
|-------|-------------|--------|
| API `/api/v1/analysis/unified` | Accepts files, returns JSON | ✅ |
| API `/api/v1/user/history` | Returns analysis history | ✅ |
| Export `/api/v1/results/{id}/export` | Creates PDF/DOCX/XLSX | 🔶 |
| FE upload → analysis | Displays result | ✅ |
| FE chat | Sends and receives responses | 🔶 |
| FE/BE variables | Match and validate | ✅ |
| Render | Service accessible online | ✅ |

---

## 🧩 Scientific Prompt Engineering Methodology

### Process

1. ✅ Collect data and concept
2. ✅ Formulate hypothesis
3. ✅ Create test prototype
4. 🔶 Simulate agents
5. 🔶 Output final synchronized system

### Principles

- ✅ Code is explainable
- ✅ Code is extensible
- ✅ Code is reproducible

---

## 📝 Current Implementation Status

### ✅ Fully Implemented

- FastAPI backend with modular architecture
- React + TypeScript frontend with Vite
- Czech localization (cs.json)
- Centralized LLM service (Claude + OpenAI + Perplexity)
- TZD Reader agent
- Upload API with validation
- File storage system
- CORS configuration
- Dockerfile for deployment
- Router registry system

### 🔶 Partially Implemented

- Multi-agent orchestration (framework exists)
- Export functionality (structure ready)
- Chat interface (UI ready)

### 📋 Planned / To Be Extended

- Additional agents (BOQ, Drawing, Resource, etc.)
- Knowledge base API
- Full export pipeline (PDF/DOCX/XLSX)
- Pre-commit hooks
- Extended test coverage

---

## 🔗 Related Documentation

- **[Implementation Status Report](../IMPLEMENTATION_STATUS.md)** - Current implementation progress
- [Architecture Flow](../ARCHITECTURE_FLOW.md)
- [Modular Architecture](./architecture/stav-agent-modular-arch.md)
- [TZD Reader](../TZD_READER_README.md)
- [Quick Reference](../QUICK_REFERENCE.md)
- [API Documentation](../README.md)

---

**Last Updated:** 2025-01-04  
**Version:** 1.5-CZ  
**Status:** Active Development (60% complete - see [Implementation Status](../IMPLEMENTATION_STATUS.md))
