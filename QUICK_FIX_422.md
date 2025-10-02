# Quick Fix Guide - 422 Error

## Problem
Getting 422 error when uploading files to `/api/v1/analysis/unified`

## Root Cause
**Two issues:**
1. Sending metadata fields that backend doesn't expect: `ai_engine`, `language`, `project_name`
2. Manually setting `Content-Type` header (prevents proper boundary generation)

## Solution

### ❌ WRONG (Causes 422)
```typescript
const formData = new FormData();
technicalFiles.forEach(file => formData.append('technical_files', file));
quantitiesFiles.forEach(file => formData.append('quantities_files', file));
drawingsFiles.forEach(file => formData.append('drawings_files', file));

// ❌ DON'T DO THIS:
formData.append('ai_engine', 'auto');
formData.append('language', 'en');
formData.append('project_name', 'My Project');

// ❌ DON'T DO THIS:
const response = await apiClient.post('/api/v1/analysis/unified', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',  // Missing boundary!
  }
});
```

### ✅ CORRECT (Works)
```typescript
const formData = new FormData();
technicalFiles.forEach(file => formData.append('technical_files', file));
quantitiesFiles.forEach(file => formData.append('quantities_files', file));
drawingsFiles.forEach(file => formData.append('drawings_files', file));

// ✅ NO metadata fields
// ✅ NO manual Content-Type header

const response = await apiClient.post('/api/v1/analysis/unified', formData, {
  timeout: 300000, // Optional: 5 minute timeout
});
```

## Why This Works

### Backend Endpoint Only Accepts
```python
@router.post("/unified")
async def analyze_files(
    technical_files: Optional[List[UploadFile]] = File(None),
    quantities_files: Optional[List[UploadFile]] = File(None),
    drawings_files: Optional[List[UploadFile]] = File(None)
):
```

### FastAPI Validation
- Any field NOT in the signature → **422 Error**
- Only send what the backend expects

### Content-Type with FormData
- Browser automatically adds: `Content-Type: multipart/form-data; boundary=...`
- Setting it manually removes the boundary
- Let Axios/fetch handle it automatically

## Key Rules

1. ✅ **Only send file arrays**: `technical_files`, `quantities_files`, `drawings_files`
2. ❌ **Don't send metadata**: No `ai_engine`, `language`, `project_name`, etc.
3. ❌ **Don't set Content-Type**: Let the library handle it
4. ✅ **You can set other options**: `timeout`, `onUploadProgress`, etc.

## Testing

```bash
# Test endpoint with curl
curl -X POST http://localhost:8000/api/v1/analysis/unified \
  -F "technical_files=@file.pdf"

# Should return 200 OK
```

## Files Changed
- `frontend/src/pages/ProjectAnalysis.tsx` (lines 61-79)
  - Removed 3 metadata appends
  - Removed manual Content-Type header
  - Added explanatory comment

## Documentation
- Full details: `FIX_422_METADATA.md`
- Visual guide: `VISUAL_FIX_422_METADATA.md`
- Russian guide: `РЕШЕНИЕ_ОШИБКИ_422_МЕТАДАННЫЕ.md`
- Original fix: `FIX_422_ERROR.md`
- Best practices: `РЕШЕНИЕ_422_ОШИБКИ.md`

---

**Status**: ✅ Fixed
**Impact**: Minimal (7 lines removed, 1 comment added)
**Breaking Changes**: None
