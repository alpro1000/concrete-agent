# Fix for 422 Error - Metadata Fields Removal

## Problem
The frontend was still getting 422 (Unprocessable Entity) errors when uploading files to `/api/v1/analysis/unified` endpoint.

## Root Cause
The frontend code in `ProjectAnalysis.tsx` was sending **extra metadata fields** that the backend endpoint does NOT accept:

### ❌ Previous Code (Lines 75-78)
```typescript
// Add metadata
formData.append('ai_engine', 'auto');
formData.append('language', localStorage.getItem('i18nextLng') || 'en');
formData.append('project_name', 'Project Analysis');
```

These fields are NOT in the backend endpoint signature:
```python
@router.post("/unified")
async def analyze_files(
    technical_files: Optional[List[UploadFile]] = File(None),
    quantities_files: Optional[List[UploadFile]] = File(None),
    drawings_files: Optional[List[UploadFile]] = File(None)
):
```

FastAPI's automatic validation rejects requests with unexpected parameters, returning 422.

## Additional Issue
The frontend was also manually setting the `Content-Type` header (lines 82-84):

### ❌ Previous Code
```typescript
const response = await apiClient.post('/api/v1/analysis/unified', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',  // DON'T SET MANUALLY
  },
  timeout: 300000,
});
```

This is problematic because:
1. The browser needs to add a `boundary` parameter to `Content-Type`
2. Manually setting it without a boundary causes parsing issues
3. Axios automatically sets the correct header for FormData

## Solution

### Changes Made to `frontend/src/pages/ProjectAnalysis.tsx`

**Lines 61-79** (before):
```typescript
try {
  const formData = new FormData();
  
  // Add files from each panel
  technicalFiles.forEach(file => {
    formData.append('technical_files', file);
  });
  quantitiesFiles.forEach(file => {
    formData.append('quantities_files', file);
  });
  drawingsFiles.forEach(file => {
    formData.append('drawings_files', file);
  });

  // Add metadata
  formData.append('ai_engine', 'auto');
  formData.append('language', localStorage.getItem('i18nextLng') || 'en');
  formData.append('project_name', 'Project Analysis');

  // Use the new unified analysis endpoint
  const response = await apiClient.post('/api/v1/analysis/unified', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5 minutes
  });
```

**Lines 61-79** (after):
```typescript
try {
  const formData = new FormData();
  
  // Add files from each panel
  technicalFiles.forEach(file => {
    formData.append('technical_files', file);
  });
  quantitiesFiles.forEach(file => {
    formData.append('quantities_files', file);
  });
  drawingsFiles.forEach(file => {
    formData.append('drawings_files', file);
  });

  // Use the new unified analysis endpoint
  // Note: Do not manually set Content-Type header - Axios handles it automatically for FormData
  const response = await apiClient.post('/api/v1/analysis/unified', formData, {
    timeout: 300000, // 5 minutes
  });
```

### What Was Removed:
1. ❌ `formData.append('ai_engine', 'auto')`
2. ❌ `formData.append('language', localStorage.getItem('i18nextLng') || 'en')`
3. ❌ `formData.append('project_name', 'Project Analysis')`
4. ❌ Manual `Content-Type: multipart/form-data` header

### What Remains:
1. ✅ Only the three file arrays: `technical_files`, `quantities_files`, `drawings_files`
2. ✅ Proper timeout setting (5 minutes)
3. ✅ Axios automatically sets correct `Content-Type` with boundary

## Verification

### Build Test
```bash
cd frontend
npm install
npm run build
```

**Result**: ✅ Build successful (6.73s)

### Expected Behavior
- **Before fix**: 422 error with metadata fields
- **After fix**: 200 OK with file processing results

### Manual Testing
To verify the fix works:

1. Start the backend:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. Test with curl (simulating NEW frontend):
```bash
echo "test" > /tmp/test.pdf
curl -X POST http://localhost:8000/api/v1/analysis/unified \
  -F "technical_files=@/tmp/test.pdf"
```

Expected: 200 OK with JSON response

3. Test with metadata (simulating OLD frontend):
```bash
curl -X POST http://localhost:8000/api/v1/analysis/unified \
  -F "technical_files=@/tmp/test.pdf" \
  -F "ai_engine=auto"
```

Expected: 422 error (metadata field not recognized)

## References

This fix aligns with the documentation in:
- `РЕШЕНИЕ_422_ОШИБКИ.md` lines 53-65 (best practices for FormData)
- `РЕШЕНИЕ_422_ОШИБКИ.md` lines 110-137 (don't set Content-Type manually)
- `FIX_422_ERROR.md` (backend endpoint signature)

## Impact
- **Files Changed**: 1 file (`frontend/src/pages/ProjectAnalysis.tsx`)
- **Lines Changed**: Removed 4 lines (metadata), removed 3 lines (headers), added 1 comment
- **Breaking Changes**: None
- **Backward Compatibility**: Maintained (backend still accepts same files)

## Summary
The 422 error was caused by sending metadata fields that the FastAPI endpoint doesn't accept. Removing these fields and letting Axios handle the Content-Type header resolves the issue. The frontend now sends ONLY what the backend expects: three optional file arrays.
