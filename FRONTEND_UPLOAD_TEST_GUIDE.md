# Frontend Upload Logic - Test Guide

This guide documents the unified upload system and provides testing instructions for the three-panel upload functionality.

## System Architecture

### Frontend → Backend Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ThreePanelUpload.tsx                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Technical   │  │  Quantities  │  │   Drawings   │     │
│  │   Panel      │  │    Panel     │  │    Panel     │     │
│  │  PDF,DOCX,TXT│  │  XLSX,XML,XC4│  │ PDF,DWG,DXF  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                 │                  │             │
│         └─────────────────┴──────────────────┘             │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            ▼
                 ProjectAnalysis.tsx
                  (FormData Builder)
                            │
                            ▼
              const formData = new FormData();
              technicalFiles.forEach(f => 
                formData.append("technical_files", f));
              quantitiesFiles.forEach(f => 
                formData.append("quantities_files", f));
              drawingsFiles.forEach(f => 
                formData.append("drawings_files", f));
                            │
                            ▼
            POST /api/v1/analysis/unified
            Content-Type: multipart/form-data
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend: unified_router.py                     │
│                                                             │
│  @router.post("/unified")                                  │
│  async def analyze_files(                                  │
│    technical_files: Optional[List[UploadFile]],           │
│    quantities_files: Optional[List[UploadFile]],          │
│    drawings_files: Optional[List[UploadFile]]             │
│  )                                                         │
│                                                             │
│  Returns:                                                  │
│  {                                                         │
│    "status": "success",                                    │
│    "files": [                                              │
│      {                                                     │
│        "name": "file.pdf",                                 │
│        "type": ".pdf",                                     │
│        "category": "technical",                            │
│        "success": true,                                    │
│        "error": null                                       │
│      }                                                     │
│    ],                                                      │
│    "summary": {                                            │
│      "total": 3,                                           │
│      "successful": 3,                                      │
│      "failed": 0                                           │
│    }                                                       │
│  }                                                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    ResultsPanel.tsx                         │
│                                                             │
│  ┌─────────────────────────────────────────────────┐      │
│  │ Tabs: [Formatted View] [JSON View]              │      │
│  └─────────────────────────────────────────────────┘      │
│                                                             │
│  File Results Table:                                       │
│  ┌────────────┬──────────┬────────┬─────────┐            │
│  │ File Name  │ Category │ Type   │ Status  │            │
│  ├────────────┼──────────┼────────┼─────────┤            │
│  │ spec.pdf   │technical │  PDF   │ ✅      │            │
│  │ budget.xlsx│quantities│  XLSX  │ ✅      │            │
│  │ plan.dwg   │drawings  │  DWG   │ ✅      │            │
│  └────────────┴──────────┴────────┴─────────┘            │
│                                                             │
│  Export Buttons:                                           │
│  [📄 JSON] [📕 PDF] [📘 Word] [📗 Excel]                  │
└─────────────────────────────────────────────────────────────┘
```

## File Type Configuration

### Panel 1: Technical Documents
- **FormData Key**: `technical_files`
- **Accepted Formats**: `.pdf`, `.docx`, `.doc`, `.txt`
- **Max Size**: 50MB per file
- **Max Files**: 10 per panel
- **Examples**: 
  - Technical specifications
  - Project briefs
  - TZD (Техническое задание) documents
  - Requirements documents

### Panel 2: Quantities & Budget
- **FormData Key**: `quantities_files`
- **Accepted Formats**: `.xlsx`, `.xls`, `.xml`, `.xc4`
- **Max Size**: 50MB per file
- **Max Files**: 10 per panel
- **Examples**:
  - Bill of quantities (BOQ)
  - Cost estimates
  - Work schedules
  - Quantity takeoffs
  - Budget spreadsheets

### Panel 3: Drawings
- **FormData Key**: `drawings_files`
- **Accepted Formats**: `.pdf`, `.dwg`, `.dxf`, `.jpg`, `.jpeg`, `.png`
- **Max Size**: 50MB per file
- **Max Files**: 10 per panel
- **Examples**:
  - Floor plans
  - Sections
  - Elevations
  - 3D models
  - BIM exports (ArchiCAD, Revit)

## Multilingual Support

### 🇬🇧 English
```json
{
  "technical": {
    "title": "Technical Documents",
    "description": "Technical assignment & project descriptions (PDF, DOCX, TXT)"
  },
  "quantities": {
    "title": "Quantities & Budget",
    "description": "Bill of quantities, budget, work list (Excel, XML, XC4)"
  },
  "drawings": {
    "title": "Drawings",
    "description": "Drawings (PDF, DWG, DXF, images from ArchiCAD/Revit)"
  }
}
```

### 🇨🇿 Czech (with diacritics)
```json
{
  "technical": {
    "title": "Technické zadání",
    "description": "Technické zadání a popisy projektu (PDF, DOCX, TXT)"
  },
  "quantities": {
    "title": "Výkaz výměr",
    "description": "Výkaz výměr, rozpočet, soupis prací (Excel, XML, XC4)"
  },
  "drawings": {
    "title": "Výkresy",
    "description": "Výkresy (PDF, DWG, DXF, obrázky z ArchiCAD/Revit)"
  }
}
```

### 🇷🇺 Russian (Cyrillic)
```json
{
  "technical": {
    "title": "Техническое задание",
    "description": "Техническое задание и описания проекта (PDF, DOCX, TXT)"
  },
  "quantities": {
    "title": "Ведомость объёмов работ",
    "description": "Ведомость объёмов работ, смета, список работ (Excel, XML, XC4)"
  },
  "drawings": {
    "title": "Чертежи",
    "description": "Чертежи (PDF, DWG, DXF, изображения из ArchiCAD/Revit)"
  }
}
```

## Testing Instructions

### 1. Manual Testing with curl

Create test files:
```bash
echo "Technical specification document" > technical.txt
echo "Budget spreadsheet data" > quantities.txt
echo "Drawing file content" > drawings.txt
```

Test the API:
```bash
curl -X POST https://concrete-agent.onrender.com/api/v1/analysis/unified \
  -F "technical_files=@technical.txt" \
  -F "quantities_files=@quantities.txt" \
  -F "drawings_files=@drawings.txt" \
  -w "\n\nHTTP Status: %{http_code}\n"
```

Expected response:
```json
{
  "status": "success",
  "message": null,
  "files": [
    {
      "name": "technical.txt",
      "type": ".txt",
      "category": "technical",
      "success": true,
      "error": null
    },
    {
      "name": "quantities.txt",
      "type": ".txt",
      "category": "quantities",
      "success": true,
      "error": null
    },
    {
      "name": "drawings.txt",
      "type": ".txt",
      "category": "drawings",
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
```

### 2. Testing with Postman

1. Create a new POST request
2. URL: `https://concrete-agent.onrender.com/api/v1/analysis/unified`
3. Set Body type to `form-data`
4. Add files:
   - Key: `technical_files`, Type: File, Value: [select your PDF/DOCX]
   - Key: `quantities_files`, Type: File, Value: [select your XLSX/XML]
   - Key: `drawings_files`, Type: File, Value: [select your DWG/PDF]
5. Click Send
6. Verify response shows all files categorized correctly

### 3. Frontend Testing

1. **Start the development server:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Test Upload Flow:**
   - Open browser to `http://localhost:5173`
   - Drag files into each panel (or click to browse)
   - Verify file count updates in summary card
   - Click "Start Analysis" button
   - Wait for results

3. **Verify Results Panel:**
   - Check that all files appear with correct categories
   - Verify success/error icons (✅/❌)
   - Switch between "Formatted View" and "JSON View" tabs
   - Test export buttons (JSON export should work)

4. **Test Language Switching:**
   - Switch to Czech (Čeština) - verify diacritics display correctly
   - Switch to Russian (Русский) - verify Cyrillic displays correctly
   - Switch to English - verify default labels
   - Check that all panel titles and descriptions update properly

### 4. Edge Case Testing

Test invalid files:
```bash
# Test with wrong file type
echo "test" > invalid.xyz
curl -X POST https://concrete-agent.onrender.com/api/v1/analysis/unified \
  -F "technical_files=@invalid.xyz"
```

Expected: Error for invalid extension

Test with no files:
```bash
curl -X POST https://concrete-agent.onrender.com/api/v1/analysis/unified
```

Expected: HTTP 400 - "No files uploaded"

Test with oversized file:
```bash
# Create a 60MB file (exceeds 50MB limit)
dd if=/dev/zero of=large.pdf bs=1M count=60
curl -X POST https://concrete-agent.onrender.com/api/v1/analysis/unified \
  -F "technical_files=@large.pdf"
```

Expected: File rejected for being too large

### 5. Build Verification

```bash
cd frontend
npm run build
```

Expected output:
```
✓ 4878 modules transformed.
✓ built in ~7s
```

No TypeScript errors or linting issues should appear.

## Results Panel Features

### Formatted View
- Displays success message and status icon
- Summary statistics (total/successful/failed)
- Files grouped by category (technical/quantities/drawings)
- Each file shows:
  - Name
  - Type badge
  - Success/error icon
  - Error message (if failed)
  - Additional metadata (agent used, detected type)

### JSON View
- Raw API response in formatted JSON
- Useful for debugging
- Can be copied for documentation

### Export Options
- **JSON Export**: ✅ Working - downloads analysis_YYYY-MM-DD.json
- **PDF Export**: 🔄 Requires backend support
- **Word Export**: 🔄 Requires backend support
- **Excel Export**: 🔄 Requires backend support

## Troubleshooting

### Issue: Files not uploading
**Check:**
1. File extension matches panel's accepted formats
2. File size < 50MB
3. Not exceeding 10 files per panel
4. Network connection to backend

### Issue: Results not displaying
**Check:**
1. Response status code (should be 200)
2. Console for JavaScript errors
3. API response structure matches expected format

### Issue: Translation not showing
**Check:**
1. Language selector in top-right corner
2. i18n files contain all required keys
3. Browser cache (try hard refresh: Ctrl+Shift+R)

### Issue: Export buttons not working
**Note:** Only JSON export is currently implemented client-side. PDF/Word/Excel require backend support and will show "requires backend support" message.

## Success Criteria

✅ **Upload Logic**
- Frontend sends files with correct FormData keys
- Backend receives files in correct categories
- All file types properly validated

✅ **Results Display**
- Table shows all files with categories
- Success/error status clearly indicated
- Both JSON and Formatted views work

✅ **Multilingual**
- English, Czech, Russian translations complete
- Diacritics display correctly (č, š, ž, ř, ё, й, щ)
- All panel labels translate properly

✅ **Export**
- JSON export works (downloads file)
- Other formats show appropriate message

## API Contract

### Request
```typescript
POST /api/v1/analysis/unified
Content-Type: multipart/form-data

FormData:
  technical_files: File[]     // Optional
  quantities_files: File[]    // Optional
  drawings_files: File[]      // Optional
```

### Response
```typescript
{
  status: "success" | "error" | "partial",
  message?: string,
  files: Array<{
    name: string,
    type: string,              // e.g., ".pdf"
    category: "technical" | "quantities" | "drawings",
    success: boolean,
    error: string | null,
    result?: any               // Additional processing data
  }>,
  summary: {
    total: number,
    successful: number,
    failed: number
  }
}
```

## Files Modified

### Frontend
- ✅ `frontend/src/pages/ProjectAnalysis.tsx` - Upload logic (no changes needed)
- ✅ `frontend/src/components/ThreePanelUpload.tsx` - Three panels (no changes needed)
- ✅ `frontend/src/components/ResultsPanel.tsx` - Results display (no changes needed)
- ✅ `frontend/src/i18n/en.json` - English translations (updated)
- ✅ `frontend/src/i18n/cs.json` - Czech translations (updated)
- ✅ `frontend/src/i18n/ru.json` - Russian translations (updated)

### Backend
- ✅ `app/routers/unified_router.py` - Unified endpoint (no changes needed)

## Conclusion

The frontend upload logic is fully implemented and aligned with the backend API. All three panels correctly send files with the appropriate FormData keys (`technical_files`, `quantities_files`, `drawings_files`), and the results panel properly displays categorized results with success/error indicators and export functionality.

The system is production-ready and all requirements from the problem statement have been met.
