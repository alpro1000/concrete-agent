# Quick Reference Guide

## For Developers

### Backend Changes

#### 1. Using the PromptLoader
```python
from app.core.prompt_loader import get_prompt_loader

# Get singleton instance
loader = get_prompt_loader()

# Use it
prompt_text = loader.get_prompt("gpt-4.1", "example_prompt")
```

#### 2. Unified Router Response Format
```python
# Success Response (HTTP 200)
{
    "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "success",
    "files": [
        {
            "name": "file.pdf",
            "type": "pdf",
            "category": "technical",
            "success": true,
            "error": null
        }
    ],
    "summary": {
        "total": 3,
        "successful": 3,
        "failed": 0
    }
}

# Partial Success (HTTP 200)
{
    "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "partial",
    "files": [
        {
            "name": "valid.pdf",
            "type": "pdf",
            "category": "technical",
            "success": true,
            "error": null
        },
        {
            "name": "invalid.exe",
            "type": "exe",
            "category": "technical",
            "success": false,
            "error": "Invalid file type 'application/x-msdownload' for technical"
        }
    ],
    "summary": {
        "total": 2,
        "successful": 1,
        "failed": 1
    }
}

# All Failed (HTTP 200)
{
    "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "error",
    "files": [
        {
            "name": "invalid.exe",
            "type": "exe",
            "category": "technical",
            "success": false,
            "error": "Invalid file type"
        }
    ],
    "summary": {
        "total": 1,
        "successful": 0,
        "failed": 1
    }
}

# No Files (HTTP 400)
{
    "detail": "No files uploaded"
}
```

#### 3. File Validation Rules
```python
# Allowed Extensions
extensions = [
    '.pdf', '.docx', '.txt',           # Documents
    '.xlsx', '.xls', '.xml', '.xc4',   # Spreadsheets
    '.dwg', '.dxf',                    # CAD
    '.png', '.jpg', '.jpeg'            # Images
]

# Max file size
MAX_SIZE = 50 * 1024 * 1024  # 50 MB
```

### Frontend Changes

#### 1. API Configuration
```typescript
// In your component
import apiClient from '../api/client';

// API client automatically uses environment configuration
const response = await apiClient.post('/api/v1/analysis/unified', formData);
```

#### 2. Environment Variables
```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000

# .env.production
VITE_API_BASE_URL=https://concrete-agent.onrender.com
```

#### 3. Using ResultsPanel Component
```typescript
import ResultsPanel from '../components/ResultsPanel';

// In your component
const [results, setResults] = useState(null);

// After receiving response
<ResultsPanel 
  results={results} 
  loading={loading}
  onClose={() => setResults(null)}
/>
```

#### 4. Response Type
```typescript
interface AnalysisResult {
  status: 'success' | 'error';
  message?: string;
  files: Array<{
    name: string;
    type: string;
    category?: string;
    success: boolean;
    error: string | null;
    result?: any;
  }>;
  summary: {
    total: number;
    successful: number;
    failed: number;
  };
  project_name?: string;
  language?: string;
  timestamp?: string;
}
```

## For Testers

### API Testing with curl

#### Success Case
```bash
curl -X POST http://localhost:8000/api/v1/analysis/unified \
  -F "technical_files=@document.pdf" \
  -F "quantities_files=@data.xlsx" \
  -F "language=en" \
  -F "project_name=Test Project"
```

#### Expected Response (200)
```json
{
  "status": "success",
  "message": "All 2 file(s) processed successfully",
  "files": [
    {
      "name": "document.pdf",
      "type": "pdf",
      "category": "technical",
      "success": true,
      "error": null
    },
    {
      "name": "data.xlsx",
      "type": "xlsx",
      "category": "quantities",
      "success": true,
      "error": null
    }
  ],
  "summary": {
    "total": 2,
    "successful": 2,
    "failed": 0
  }
}
```

#### Validation Error Case
```bash
curl -X POST http://localhost:8000/api/v1/analysis/unified \
  -F "technical_files=@malicious.exe"
```

#### Expected Response (400)
```json
{
  "status": "error",
  "message": "All 1 file(s) failed to process",
  "files": [
    {
      "name": "malicious.exe",
      "type": "exe",
      "category": "technical",
      "success": false,
      "error": "Invalid extension '.exe'. Allowed: .docx, .dwg, ..."
    }
  ],
  "summary": {
    "total": 1,
    "successful": 0,
    "failed": 1
  }
}
```

### Frontend Testing

#### 1. Start Development Server
```bash
cd frontend
npm install
npm run dev
```

#### 2. Test Upload Flow
1. Open http://localhost:5173
2. Navigate to Project Analysis
3. Upload files from each panel
4. Click "Analyze"
5. Verify ResultsPanel displays correctly
6. Test export functionality

#### 3. Test Error Handling
- Upload invalid file (.exe) → Should show error
- Upload oversized file (>50MB) → Should show error
- Disconnect backend → Should show network error
- Upload valid files → Should show success

## For DevOps

### Environment Variables

#### Backend
```bash
# In production environment
PORT=8000
# Add any API keys as needed
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

#### Frontend
```bash
# .env.production
VITE_API_BASE_URL=https://your-backend-url.com
```

### Deployment Checklist

- [ ] Install backend dependencies: `pip install -r requirements.txt`
- [ ] Set environment variables for API keys
- [ ] Start backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [ ] Build frontend: `npm run build`
- [ ] Set `VITE_API_BASE_URL` in production environment
- [ ] Deploy frontend build to static hosting
- [ ] Test end-to-end flow
- [ ] Verify CORS settings in `app/main.py`

### Health Check Endpoints

```bash
# Backend health
curl http://localhost:8000/health

# Unified router health
curl http://localhost:8000/api/v1/analysis/health
```

## Troubleshooting

### Backend Issues

#### Issue: Import error for prompt_loader
```python
# Solution: Ensure correct import
from app.core.prompt_loader import get_prompt_loader
```

#### Issue: Files not cleaned up
```python
# Check: finally block in unified_router.py
# Should delete all temp files even on error
```

#### Issue: Wrong HTTP status code
```python
# Verify:
# - 200: All successful
# - 207: Some failed
# - 400: All failed validation
# - 500: Server error
```

### Frontend Issues

#### Issue: API URL not working
```bash
# Check environment variable
echo $VITE_API_BASE_URL

# Verify fallback logic in api/client.ts
# Should use: env var → prod URL → dev URL
```

#### Issue: Results not displaying
```typescript
// Check: ResultsPanel receives results prop
<ResultsPanel results={analysisResult} loading={loading} />

// Verify: analysisResult matches new format
// Should have: status, message, files, summary
```

#### Issue: Export not working
```typescript
// JSON export should work immediately
// PDF/Word/Excel require backend endpoints
```

## Migration from Old Format

### Backend Response Migration

#### Old Format (DEPRECATED)
```json
{
  "success": true,
  "technical_summary": [...],
  "quantities_summary": [...],
  "combined_results": {...}
}
```

#### New Format (CURRENT)
```json
{
  "status": "success",
  "message": "...",
  "files": [...],
  "summary": {...}
}
```

### Frontend Code Migration

#### Old Code (DEPRECATED)
```typescript
if (response.data.success) {
  // Handle success
}
```

#### New Code (CURRENT)
```typescript
if (response.status === 200 || response.status === 207) {
  if (response.data.status === 'success') {
    // Handle success
  }
}
```

## Quick Commands

### Development
```bash
# Backend
cd /path/to/concrete-agent
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Testing
```bash
# Backend syntax check
python -m py_compile app/routers/unified_router.py

# Test prompt loader
python -c "from app.core.prompt_loader import get_prompt_loader; print(get_prompt_loader())"

# Frontend build
cd frontend
npm run build
```

### Production
```bash
# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend build
cd frontend
npm run build
# Deploy dist/ folder to static hosting
```

## Support

### Documentation Files
1. `REFACTORING_SUMMARY.md` - Technical details
2. `IMPLEMENTATION_CHECKLIST.md` - Verification checklist  
3. `ARCHITECTURE_FLOW.md` - Visual diagrams
4. `FINAL_IMPLEMENTATION_REPORT.md` - Executive summary

### Key Files to Review
- Backend: `app/routers/unified_router.py`
- Frontend: `frontend/src/components/ResultsPanel.tsx`
- API Config: `frontend/src/api/client.ts`
- Environment: `frontend/.env.*`

---

*Last Updated: 2024-10-01*  
*Version: 2.0.0*
