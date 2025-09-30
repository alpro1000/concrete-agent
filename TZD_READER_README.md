# TZD Reader - Minimal Configuration

This project has been cleaned up to contain only the **TZD Reader** (Technical Assignment Reader) functionality.

## 🎯 What Was Done

### Backend Cleanup
✅ **Removed agents:**
- concrete_agent
- dwg_agent  
- material_agent
- smetny_inzenyr
- volume_agent

✅ **Removed routers:**
- analyze_concrete.py
- analyze_materials.py
- compare.py
- corrections.py
- documents.py
- extractions.py
- project.py
- projects.py
- upload.py

✅ **Removed prompts:**
- concrete_prompt.json
- material_prompt.json
- materials_prompt.json
- orchestrator_prompt.json
- volume_prompt.json

✅ **Kept only:**
- `agents/tzd_reader/` - TZD Reader agent
- `app/routers/tzd_router.py` - TZD API router
- `app/prompts/tzd_prompt.json` - TZD prompt
- `app/core/` - Core services (LLM, prompt loader, etc.)

### Frontend Cleanup
✅ **Removed pages:**
- Home.tsx
- Analysis.tsx
- Reports.tsx

✅ **Removed components:**
- FileUpload.tsx
- LogsDisplay.tsx
- ResultsChart.tsx
- ResultsTable.tsx
- TZDResults.tsx
- TZDUpload.tsx

✅ **Kept only:**
- `TZDAnalysis.tsx` - Main TZD analysis page
- `TZDUploadSimple.tsx` - 3-column upload component
- `LanguageSelector.tsx` - Language selector

### Features Added
✅ **Hybrid Parsing:**
- Standard parsers (pdfminer, docx, openpyxl)
- MinerU integration (if available)
- Automatic fallback to standard parsers if MinerU fails

✅ **Diacritics Normalization:**
- Automatic Unicode NFC normalization
- Applied to all parsed text
- Applied to all analysis results
- Fixes Czech, Russian, and other diacritics

✅ **Multi-language Support:**
- Three-column upload interface (PDF, DOCX, TXT)
- Project description translation display (RU, CS, EN)
- All text normalized for proper diacritics

✅ **LLM Integration:**
- Centralized LLMService
- Dynamic provider selection (GPT, Claude, Perplexity)
- Based on available API keys

## 🚀 Running the System

### Backend
```bash
cd /home/runner/work/concrete-agent/concrete-agent
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Access Swagger UI at: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev      # Development mode
npm run build    # Production build
```

## 📡 API Endpoints

Only TZD Reader endpoints are available:

- `POST /api/v1/tzd/analyze` - Analyze technical documents
- `GET /api/v1/tzd/health` - Health check
- `GET /api/v1/tzd/analysis/{analysis_id}` - Get analysis result

## 🔑 Environment Variables

Required for full functionality:

```bash
# AI Provider Keys (at least one required)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
PERPLEXITY_API_KEY=your_perplexity_key

# Optional
OPENAI_MODEL=gpt-4o-mini
CLAUDE_MODEL=claude-3-5-sonnet-20241022
MINERU_ENABLED=false  # Set to true to enable MinerU
```

## 📝 Upload Formats

The system accepts three document formats:
- **PDF** (.pdf) - Maximum 10MB
- **DOCX** (.docx) - Maximum 10MB  
- **TXT** (.txt) - Maximum 10MB

## 🔒 Security Features

- File extension validation
- File size limits (10MB per file)
- Path traversal protection
- Safe temporary file handling
- Automatic cleanup after analysis

## 📊 Analysis Output

The TZD Reader extracts and returns:
- `project_object` - Project description
- `requirements` - Technical requirements
- `norms` - Regulatory standards (ČSN EN, ГОСТ, СНиП, etc.)
- `constraints` - Budget, time, technical constraints
- `environment` - Environmental conditions
- `functions` - Project functions and purpose

All text is automatically normalized for proper diacritics display.

## 🏗️ Architecture

```
Backend (FastAPI)
├── app/main.py - Main FastAPI app (TZD router only)
├── app/routers/tzd_router.py - TZD API endpoints
├── agents/tzd_reader/ - TZD Reader agent
└── app/core/ - Core services (LLM, prompt loader)

Frontend (React + TypeScript)
├── src/App.tsx - Main app (TZD page only)
├── src/pages/TZDAnalysis.tsx - Analysis page
└── src/components/TZDUploadSimple.tsx - 3-column upload
```

## ✅ Build Status

- ✅ Backend imports successfully
- ✅ Frontend builds without errors
- ✅ API endpoints operational
- ✅ File upload working
- ✅ Diacritics normalization active
- ⚠️  Analysis requires API keys (GPT/Claude/Perplexity)

## 📦 Deployment

The system is ready for deployment on Render or similar platforms:
- `npm run build` succeeds
- FastAPI app configured for production
- Static files served from frontend/dist

## 🔄 Hybrid Parsing Flow

1. **MinerU** (if enabled and available)
   - Attempts advanced PDF extraction
   - Falls back on error

2. **Standard Parsers**
   - pdfminer for PDF
   - python-docx for DOCX
   - Text file reading for TXT

3. **Diacritics Normalization**
   - Unicode NFC normalization on all text

4. **LLM Analysis**
   - Via centralized LLMService
   - Auto-selects available provider

## 🐛 Known Limitations

- Translation feature uses placeholder (needs real translation API)
- MinerU integration requires manual installation
- Analysis quality depends on API key availability

## 📧 Support

For issues or questions about TZD Reader functionality, refer to:
- `agents/tzd_reader/agent.py` - Core logic
- `app/routers/tzd_router.py` - API implementation
- Swagger UI at `/docs` for API testing
