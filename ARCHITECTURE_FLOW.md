# Architecture Flow Diagram

## Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User uploads files via ThreePanelUpload                    │
│     - Technical documents (.pdf, .docx, .txt)                  │
│     - Quantities files (.xlsx, .xls, .xml, .xc4)               │
│     - Drawings (.dwg, .dxf, .png, .jpg)                        │
│                                                                 │
│  2. ProjectAnalysis.tsx sends FormData to backend              │
│     ↓                                                           │
│  API Client (VITE_API_BASE_URL)                                │
│     - Dev: http://localhost:8000                               │
│     - Prod: https://concrete-agent.onrender.com                │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ POST /api/v1/analysis/unified
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  3. unified_router.py receives request                         │
│     ↓                                                           │
│  4. For each file:                                             │
│     a) Validate extension (unified allowed list)               │
│     b) Check size (max 50 MB)                                  │
│     c) Save to /tmp                                            │
│     d) Process with orchestrator                               │
│     e) Build file result object                                │
│                                                                 │
│  5. Determine HTTP status code:                                │
│     - All success → 200                                        │
│     - Partial success → 207                                    │
│     - All failed → 400                                         │
│     - Server error → 500                                       │
│                                                                 │
│  6. Clean up /tmp files (finally block)                        │
│                                                                 │
│  7. Return structured JSON:                                    │
│     {                                                           │
│       "status": "success" | "error",                           │
│       "message": "...",                                        │
│       "files": [{...}],                                        │
│       "summary": {                                             │
│         "total": n,                                            │
│         "successful": m,                                       │
│         "failed": k                                            │
│       }                                                         │
│     }                                                           │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ JSON Response
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Response Handler                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  8. ProjectAnalysis.tsx receives response                      │
│     - Handle status codes (200, 207, 400, 500)                │
│     - Show appropriate message/toast                           │
│     - Set analysisResult state                                 │
│                                                                 │
│  9. ResultsPanel.tsx displays results                          │
│     ┌─────────────────────────────────────────┐               │
│     │  Formatted View          JSON View      │               │
│     ├─────────────────────────────────────────┤               │
│     │                                          │               │
│     │  ✅ file1.pdf (success)                 │               │
│     │  ✅ file2.xlsx (success)                │               │
│     │  ❌ file3.exe (failed - invalid ext)    │               │
│     │                                          │               │
│     │  Summary: 2 success, 1 failed           │               │
│     │                                          │               │
│     │  [Export JSON] [Export PDF]             │               │
│     │  [Export Word] [Export Excel]           │               │
│     │                                          │               │
│     └─────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts (API_BASE_URL configuration)
│   │
│   ├── components/
│   │   ├── ThreePanelUpload.tsx (File selection)
│   │   └── ResultsPanel.tsx (NEW - Results display)
│   │
│   ├── pages/
│   │   └── ProjectAnalysis.tsx (Main page, orchestrates flow)
│   │
│   └── .env files
│       ├── .env.example (VITE_API_BASE_URL)
│       ├── .env.development (localhost:8000)
│       └── .env.production (concrete-agent.onrender.com)

app/
├── core/
│   ├── prompt_loader.py (NEW: get_prompt_loader() singleton)
│   └── orchestrator.py (File processing)
│
└── routers/
    ├── __init__.py (Exports both routers)
    ├── unified_router.py (REFACTORED - New response format)
    └── tzd_router.py (Kept as-is)
```

## Response Format Evolution

### Before (Old Format)
```json
{
  "success": true,
  "technical_summary": [...],
  "quantities_summary": [...],
  "drawings_summary": [...],
  "combined_results": {...}
}
```

### After (New Format)
```json
{
  "status": "success",
  "message": "All 3 file(s) processed successfully",
  "files": [
    {
      "name": "file.pdf",
      "type": "pdf",
      "category": "technical",
      "success": true,
      "error": null,
      "result": {...}
    }
  ],
  "summary": {
    "total": 3,
    "successful": 3,
    "failed": 0
  }
}
```

## Key Improvements

1. **Individual File Tracking**
   - Each file has its own success/error status
   - Failed files don't break the entire request
   - Clear error messages per file

2. **Proper HTTP Status Codes**
   - 200: Complete success
   - 207: Partial success (RESTful multi-status)
   - 400: Client error (validation)
   - 500: Server error

3. **Environment-Based Configuration**
   - No hardcoded URLs in components
   - Easy to change between dev/prod
   - Fallback logic for missing env vars

4. **Clean Resource Management**
   - Files saved to /tmp (standard location)
   - Automatic cleanup in finally block
   - Proper error handling during cleanup

5. **Better UX**
   - Clear visual indicators (✅/❌)
   - Grouped by category
   - Two view modes (formatted + raw JSON)
   - Ready for export functionality
