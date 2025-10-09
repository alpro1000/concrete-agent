# ARCHITECTURE GUIDE: Modern Parsing & Workflow System

## 🏗️ System Architecture Overview

This system now implements a **modern, production-ready architecture** with:

1. **Specialized Parsers** - Dedicated parsers for each document type
2. **Workflow Separation** - Clear A/B workflow split
3. **Rate Limiting** - Intelligent API quota management
4. **Fallback Strategies** - Multiple parsing methods with automatic fallback
5. **Hybrid Parsing** - Combine multiple parsers for best results

---

## 📁 New Directory Structure

```
app/
├── core/                           # Core clients and utilities
│   ├── claude_client.py            # Claude API client
│   ├── gpt4_client.py              # GPT-4 Vision client
│   ├── nanonets_client.py          # 🆕 Nanonets Document AI
│   ├── mineru_client.py            # 🆕 MinerU PDF parser
│   ├── rate_limiter.py             # 🆕 API rate limiting
│   └── config.py                   # Settings (updated)
│
├── parsers/                        # 🆕 Specialized parsers
│   ├── __init__.py
│   ├── kros_parser.py              # KROS XML parser with fallback
│   ├── pdf_parser.py               # PDF parser (MinerU + pdfplumber)
│   └── excel_parser.py             # Excel parser (pandas-based)
│
├── services/
│   ├── workflow_a.py               # ✏️ Updated with new parsers
│   ├── workflow_b.py               # 🆕 Drawing-based workflow
│   └── audit_service.py            # Audit logic
│
├── api/
│   ├── routes.py                   # Original routes
│   ├── routes_workflow_a.py        # 🆕 Workflow A endpoints
│   ├── routes_workflow_b.py        # 🆕 Workflow B endpoints
│   └── routes_parsing.py           # 🆕 Hybrid parsing
│
└── prompts/
    └── claude/
        └── generation/
            └── generate_from_drawings.txt  # 🆕 Workflow B prompt
```

---

## 🔄 Two Clear Workflows

### **Workflow A: With Existing Estimate (Výkaz výměr)**

```
1. Upload → Estimate (XML/Excel/PDF) + Documentation
2. Parse → Specialized parsers with fallback
3. Display → All positions with checkboxes
4. Select → User selects positions to analyze
5. AUDIT → Compare with KROS/RTS database
6. Classify → GREEN/AMBER/RED
7. Report → Excel Audit_Triage
```

**Endpoints:**
- `POST /api/v1/workflow-a/upload` - Upload estimate
- `GET /api/v1/workflow-a/{project_id}/positions` - Get positions
- `POST /api/v1/workflow-a/{project_id}/analyze` - Analyze selected
- `GET /api/v1/workflow-a/{project_id}/status` - Project status

### **Workflow B: Generate from Drawings (No Estimate)**

```
1. Upload → Drawings (PDF/images) + Documentation
2. Analyze → GPT-4V extracts dimensions, materials
3. Calculate → Concrete, reinforcement, formwork quantities
4. Generate → Claude creates KROS-coded positions
5. AUDIT → Validate generated positions
6. Report → Generated estimate + Tech Card
```

**Endpoints:**
- `POST /api/v1/workflow-b/upload` - Upload drawings
- `GET /api/v1/workflow-b/{project_id}/results` - Get generated estimate
- `GET /api/v1/workflow-b/{project_id}/tech-card` - Get tech card
- `GET /api/v1/workflow-b/{project_id}/status` - Project status

---

## 🛠️ Specialized Parsers

### **1. KROS Parser** (`app/parsers/kros_parser.py`)

**Supports:**
- KROS UNIXML (Soupis prací)
- KROS Table XML (Kalkulace s cenami)
- Legacy KROS formats

**Strategy:**
```
1. Try direct XML parsing
   ├─ Detect format (UNIXML/Table/Generic)
   └─ Parse with appropriate method
2. Fallback: Nanonets API (if configured)
3. Last resort: Claude with prompts
```

**Usage:**
```python
from app.parsers import KROSParser

parser = KROSParser(claude_client=claude, nanonets_client=nanonets)
result = parser.parse(Path("estimate.xml"))

# Returns:
{
    "positions": [...],
    "total_positions": 150,
    "document_info": {...},
    "format": "KROS_UNIXML"
}
```

### **2. PDF Parser** (`app/parsers/pdf_parser.py`)

**Strategy:**
```
1. Try MinerU (if installed)
   └─ High-quality table extraction
2. Fallback: pdfplumber
   └─ Extract text + tables
3. Last resort: Claude direct PDF parsing
```

**Usage:**
```python
from app.parsers import PDFParser

parser = PDFParser(claude_client=claude, mineru_client=mineru)
result = parser.parse(Path("estimate.pdf"))
```

### **3. Excel Parser** (`app/parsers/excel_parser.py`)

**Features:**
- Pandas-based parsing
- Smart column detection (handles Czech/English names)
- Multi-sheet support
- Automatic header detection

**Usage:**
```python
from app.parsers import ExcelParser

parser = ExcelParser(claude_client=claude)
result = parser.parse(Path("estimate.xlsx"))
```

---

## ⚡ Rate Limiting System

**Purpose:** Prevent API quota exhaustion

**Limits (per minute):**
- Claude: 25,000 tokens (safe margin from 30k)
- GPT-4: 8,000 tokens (safe margin from 10k)
- Nanonets: 80 calls (safe margin from 100)

**Usage:**
```python
from app.core.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# Single call with rate limiting
result = await limiter.claude_call_with_limit(
    func=claude.call,
    estimated_tokens=1500,
    prompt
)

# Batch processing
results = await limiter.batch_process_positions(
    positions=positions,
    process_func=audit_position,
    api_type='claude',
    tokens_per_position=500
)

# Get usage stats
stats = limiter.get_usage_stats()
# Returns: {"claude": {"current": 15000, "limit": 25000, ...}, ...}
```

---

## 🔌 External Service Integrations

### **Nanonets Document AI**

**Purpose:** Advanced document parsing with OCR

**Setup:**
1. Sign up at https://app.nanonets.com/
2. Train models for your document types
3. Add API key to `.env`:
   ```
   NANONETS_API_KEY=your_key_here
   ```

**Usage:**
```python
from app.core.nanonets_client import NanonetsClient

client = NanonetsClient()
result = client.extract_estimate_data(Path("estimate.pdf"))
```

### **MinerU (magic-pdf)**

**Purpose:** High-quality PDF parsing with table structure preservation

**Setup:**
```bash
pip install magic-pdf
```

**Configuration:**
```env
MINERU_OUTPUT_DIR=./temp/mineru
MINERU_OCR_ENGINE=paddle  # or tesseract
```

**Usage:**
```python
from app.core.mineru_client import MinerUClient

client = MinerUClient()
result = client.parse_pdf_estimate("estimate.pdf")
```

---

## 🌐 API Endpoints Reference

### **Hybrid Parsing**

#### `POST /api/v1/parse/hybrid`
Parse document with multiple strategies

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/parse/hybrid" \
  -F "file=@estimate.xml" \
  -F "use_nanonets=true" \
  -F "use_mineru=true" \
  -F "use_claude=true"
```

**Response:**
```json
{
  "success": true,
  "parse_id": "uuid",
  "positions": [...],
  "total_positions": 150,
  "parser_used": "kros_parser",
  "parsers_attempted": ["kros_parser"],
  "parsing_details": {...}
}
```

#### `POST /api/v1/parse/kros-xml`
Parse KROS XML specifically

#### `GET /api/v1/parse/formats`
Get supported formats and available parsers

---

## ⚙️ Configuration

### **New Settings in `.env`**

```env
# === Nanonets ===
NANONETS_API_KEY=your_nanonets_key

# === Parsing Configuration ===
PRIMARY_PARSER=claude        # Options: claude, mineru, nanonets
FALLBACK_ENABLED=true
MAX_FILE_SIZE_MB=50

# === MinerU Settings ===
MINERU_OUTPUT_DIR=./temp/mineru
MINERU_OCR_ENGINE=paddle     # paddle or tesseract

# === Rate Limiting ===
CLAUDE_TOKENS_PER_MINUTE=25000
GPT4_TOKENS_PER_MINUTE=8000
NANONETS_CALLS_PER_MINUTE=80
```

---

## 🧪 Testing

### **Test Parser Instantiation**
```python
from app.parsers import KROSParser, PDFParser, ExcelParser

# All parsers should instantiate without errors
kros = KROSParser(claude_client=claude)
pdf = PDFParser(claude_client=claude)
excel = ExcelParser(claude_client=claude)
```

### **Test API Endpoints**
```bash
# Get supported formats
curl http://localhost:8000/api/v1/parse/formats

# Upload Workflow A
curl -X POST "http://localhost:8000/api/v1/workflow-a/upload" \
  -F "estimate_file=@estimate.xml" \
  -F "project_name=Test Project"

# Upload Workflow B
curl -X POST "http://localhost:8000/api/v1/workflow-b/upload" \
  -F "drawings=@drawing1.pdf" \
  -F "drawings=@drawing2.pdf" \
  -F "project_name=Drawing Test"
```

---

## 📊 Performance Optimization

### **Parser Selection Strategy**

1. **For XML files:** Always use `KROSParser` first
2. **For PDF files:** 
   - MinerU (if installed) → Best quality
   - pdfplumber → Fast fallback
   - Claude → Last resort
3. **For Excel:** Pandas → Claude fallback

### **Rate Limiting Best Practices**

1. **Batch Processing:** Use `batch_process_positions()` for multiple items
2. **Token Estimation:** Be conservative (better to wait than fail)
3. **Monitor Usage:** Check `get_usage_stats()` regularly
4. **Adjust Limits:** Tune limits in `.env` based on your API tier

---

## 🚀 Production Deployment

### **Required Services**

1. **Core:**
   - FastAPI application
   - Claude API (required)
   
2. **Optional:**
   - GPT-4 API (for Workflow B)
   - Nanonets (for enhanced parsing)
   - MinerU (for PDF quality)
   - Perplexity (for live KB search)

### **Environment Setup**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Optional: Install MinerU
pip install magic-pdf

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **Health Checks**

```bash
# System health
curl http://localhost:8000/health

# Parser availability
curl http://localhost:8000/api/v1/parse/formats
```

---

## 🔍 Troubleshooting

### **"No positions parsed from XML"**

**Solution:**
1. Check XML format with `/api/v1/parse/formats`
2. Try hybrid parsing: `/api/v1/parse/hybrid`
3. Enable Nanonets fallback
4. Check logs for detailed error

### **"Rate limit exceeded"**

**Solution:**
1. Check current usage: `limiter.get_usage_stats()`
2. Adjust limits in `.env`
3. Implement request queuing
4. Upgrade API tier

### **"MinerU not available"**

**Solution:**
```bash
pip install magic-pdf
```

Or set `PRIMARY_PARSER=claude` in `.env`

---

## 📚 Further Reading

- [KROS XML Format Documentation](docs/kros_format.md)
- [Nanonets Setup Guide](docs/nanonets_setup.md)
- [Rate Limiting Deep Dive](docs/rate_limiting.md)
- [Workflow B Tutorial](docs/workflow_b_tutorial.md)

---

## 🎯 Next Steps

1. ✅ **Core Architecture** - Complete
2. ✅ **Parsers & Clients** - Complete
3. ✅ **Workflows A/B** - Complete
4. ✅ **API Endpoints** - Complete
5. 🔄 **Testing** - In Progress
6. 📝 **Documentation** - In Progress
7. 🚀 **Production Deploy** - Pending

---

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review error messages in API responses
3. Consult this architecture guide
4. Check individual module documentation

---

**Built with:** FastAPI, Claude AI, GPT-4 Vision, Nanonets, MinerU
**Version:** 2.0.0 (Modern Architecture)
**Last Updated:** 2024-10-09
