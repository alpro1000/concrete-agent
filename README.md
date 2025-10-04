# Construction Analysis API v2.0 🏗️

[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=for-the-badge&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00.svg?style=for-the-badge&logo=SQLAlchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

## 🚀 Features

- **Database Storage**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Multi-file Upload**: Support for simultaneous upload of multiple files
- **ZIP Support**: Automatic extraction and processing of ZIP archives
- **Self-learning Corrections**: AI agents learn from user feedback
- **Document Versioning**: File versioning with SHA256 hash comparison
- **JSON Diff**: Deep comparison of document extraction results
- **Backward Compatibility**: All existing endpoints remain functional

## 📊 Database Schema

```mermaid
erDiagram
    PROJECTS ||--o{ FOLDERS : contains
    FOLDERS ||--o{ DOCUMENTS : has
    DOCUMENTS ||--o{ EXTRACTIONS : generates
    EXTRACTIONS ||--o{ CORRECTIONS : corrected_by

    PROJECTS {
        string id PK
        varchar name
        text description
        json project_metadata
        timestamp created_at
    }
    FOLDERS {
        string id PK
        string project_id FK
        varchar name
        varchar path
        timestamp created_at
    }
    DOCUMENTS {
        string id PK
        string folder_id FK
        varchar filename
        varchar file_hash
        varchar file_type
        int version
        int size
        timestamp uploaded_at
        varchar status
        timestamp created_at
    }
    EXTRACTIONS {
        string id PK
        string document_id FK
        varchar agent
        json data
        float confidence
        timestamp created_at
    }
    CORRECTIONS {
        string id PK
        string extraction_id FK
        text user_feedback
        json corrected_data
        timestamp created_at
    }
```

## 🔧 API Endpoints

### Unified Analysis Upload (multipart/form-data)

#### POST /api/v1/analysis/unified

Upload files for analysis using multipart/form-data format. Supports both new and legacy field names for backward compatibility.

**Field Names:**
- **technical_files** or **project_documentation**: Technical documents (PDF, DOCX, TXT)
- **quantities_files** or **budget_estimate**: Budget and quantities (Excel, XML, PDF)
- **drawings_files** or **drawings**: Drawings and CAD files (PDF, DWG, DXF, images)

**Headers:**
- `Authorization: Bearer mock_jwt_token_12345` (optional, for user identification)

**Allowed MIME Types:**

| Field Type | Allowed MIME Types |
|------------|-------------------|
| technical_files / project_documentation | application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain |
| quantities_files / budget_estimate | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, application/pdf, application/xml, text/xml |
| drawings_files / drawings | application/pdf, image/jpeg, image/png, image/gif, image/bmp, application/acad, image/vnd.dwg, application/dwg, application/dxf |

**File Size Limit:** 50 MB per file (configurable via `MAX_FILE_SIZE_MB` environment variable)

**Response Format:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "files": [
    {
      "name": "technical_document.pdf",
      "type": "pdf",
      "category": "technical",
      "success": true,
      "error": null
    },
    {
      "name": "budget.xlsx",
      "type": "xlsx",
      "category": "quantities",
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
    "total": 3,
    "successful": 2,
    "failed": 1
  }
}
```

**Status Values:**
- `"success"`: All files processed successfully
- `"partial"`: Some files succeeded, some failed
- `"error"`: All files failed
- `"processing"`: Files accepted and being processed asynchronously (future use)

**Note:** The endpoint now returns 200 OK even when some files fail validation. Individual file results are returned in the `files` array with `success` and `error` fields.

**Storage:**
Files are saved to: `storage/{user_id}/uploads/{analysis_id}/`
- `user_id`: 1 for valid Bearer token, 0 otherwise
- `analysis_id`: UUID generated for this analysis
- Filenames are sanitized to prevent security issues

**Examples:**

1. **Using Swagger UI** (http://localhost:8000/docs):
   - Navigate to POST /api/v1/analysis/unified
   - Click "Try it out"
   - Use file upload buttons to select files for each field
   - Add Authorization header: `Bearer mock_jwt_token_12345`
   - Click "Execute"

2. **Using curl (single file per field):**
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/unified" \
  -H "Authorization: Bearer mock_jwt_token_12345" \
  -F "technical_files=@/path/to/technical.pdf" \
  -F "quantities_files=@/path/to/budget.xlsx" \
  -F "drawings_files=@/path/to/drawing.pdf"
```

3. **Using curl (multiple files in one field):**
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/unified" \
  -H "Authorization: Bearer mock_jwt_token_12345" \
  -F "technical_files=@/path/to/tech1.pdf" \
  -F "technical_files=@/path/to/tech2.docx" \
  -F "drawings_files=@/path/to/drawing1.dwg" \
  -F "drawings_files=@/path/to/drawing2.pdf"
```

4. **Using curl (legacy field names):**
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/unified" \
  -H "Authorization: Bearer mock_jwt_token_12345" \
  -F "project_documentation=@/path/to/project.pdf" \
  -F "budget_estimate=@/path/to/estimate.xlsx" \
  -F "drawings=@/path/to/plan.pdf"
```

5. **Using Python requests:**
```python
import requests

files = {
    'technical_files': [
        ('technical_files', open('technical.pdf', 'rb')),
        ('technical_files', open('spec.docx', 'rb'))
    ],
    'quantities_files': [
        ('quantities_files', open('budget.xlsx', 'rb'))
    ],
    'drawings_files': [
        ('drawings_files', open('drawing.dwg', 'rb'))
    ]
}

headers = {
    'Authorization': 'Bearer mock_jwt_token_12345'
}

response = requests.post(
    'http://localhost:8000/api/v1/analysis/unified',
    files=files,
    headers=headers
)

print(response.json())
```

---

### New Database-Powered Endpoints

#### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects  
- `GET /api/projects/{id}` - Project details

#### Upload & Documents
- `POST /api/projects/{id}/upload` - Multi-file upload with ZIP support
- `GET /api/projects/{id}/documents` - List documents
- `GET /api/projects/{id}/documents/{doc_id}` - Document metadata
- `GET /api/projects/{id}/documents/{doc_id}/download` - Download file

#### Extractions
- `POST /api/projects/{id}/documents/{doc_id}/extract` - Run agents manually
- `GET /api/projects/{id}/documents/{doc_id}/extractions` - List results
- `GET /api/extractions/{id}` - Extraction details

#### Corrections (Self-learning)
- `POST /api/extractions/{id}/correction` - Save user correction
- `GET /api/extractions/{id}/corrections` - List corrections

#### Compare
- `GET /api/projects/{id}/compare?doc1=UUID&doc2=UUID` - Compare documents
- `GET /api/projects/{id}/compare/concrete?doc1=UUID&doc2=UUID` - Compare concrete analysis
- `GET /api/extractions/{id1}/compare/{id2}` - Compare extractions

### Legacy Endpoints (Backward Compatible)
- `POST /analyze/concrete` - Concrete analysis
- `POST /analyze/materials` - Materials analysis  
- `POST /compare/docs` - Document comparison
- `POST /compare/smeta` - Smeta comparison
- `POST /upload/files` - Simple file upload

---

## 🌐 Production URLs and CORS

- Frontend (prod): https://stav-agent.onrender.com  
- Backend (prod): https://concrete-agent.onrender.com

### Frontend env
Set the backend base URL (Render → frontend service → Environment):
- Vite: `VITE_API_URL=https://concrete-agent.onrender.com`
- Next.js: `NEXT_PUBLIC_API_URL=https://concrete-agent.onrender.com`

Frontend must use absolute API URL from env (see `frontend/src/lib/api.ts`).

### Backend CORS
Set allowed origins (Render → backend service → Environment):
```
ALLOWED_ORIGINS=https://stav-agent.onrender.com,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```
FastAPI reads `ALLOWED_ORIGINS` and configures `CORSMiddleware`.

Подробнее см. [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_upload_contract.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Test Coverage

**Current:** 40% (8 contract tests)
- ✅ Upload endpoint contract verification
- ✅ File type validation
- ✅ Size limit enforcement (50MB)
- ✅ Multi-file upload support
- ✅ Error handling
- ✅ Response structure validation

**Test Files:**
- `tests/test_upload_contract.py` - Upload API contract tests (8 tests)

---

## 📚 Documentation

### System Architecture & Specifications
- **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - Current implementation status (60% complete)
- **[docs/QODO_SYSTEM_PROMPT.md](docs/QODO_SYSTEM_PROMPT.md)** - System specification and AI development prompt
- **[docs/architecture/stav-agent-modular-arch.md](docs/architecture/stav-agent-modular-arch.md)** - Modular "beads" architecture
- **[ARCHITECTURE_FLOW.md](ARCHITECTURE_FLOW.md)** - Visual flow diagrams
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference guide

### Agent Documentation
- **[TZD_READER_README.md](TZD_READER_README.md)** - TZD Reader agent documentation

### Implementation Reports
- **[UNIFIED_CONTRACT_IMPLEMENTATION.md](UNIFIED_CONTRACT_IMPLEMENTATION.md)** - Upload contract implementation
- **[PR_SUMMARY.md](PR_SUMMARY.md)** - Pull request summary
- **[BEFORE_AFTER_CONTRACT.md](BEFORE_AFTER_CONTRACT.md)** - Contract comparison

---

## 🤝 Contributing

1. Check [AUDIT_CHECKLIST.md](AUDIT_CHECKLIST.md) for prioritized tasks
2. Run tests before submitting: `pytest tests/ -v`
3. Ensure code follows existing patterns
4. Update documentation if needed
