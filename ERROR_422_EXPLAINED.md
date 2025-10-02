# Error Analysis - 422 Status Code Explained

## Original Error Message (from Problem Statement)

```javascript
{
  message: 'Request failed with status code 422',
  name: 'AxiosError',
  code: 'ERR_BAD_REQUEST',
  response: {
    status: 422,
    statusText: "",
    data: {
      detail: Array(1)
    }
  }
}
```

## What This Error Means

### HTTP 422: Unprocessable Entity
- **Category**: Client Error
- **Meaning**: The request was well-formed but semantically incorrect
- **FastAPI Context**: The request data doesn't match the endpoint's expected parameters

### Why It Occurred

The frontend sent this FormData:
```javascript
FormData {
  'technical_files': [File objects],    // ✅ Expected by backend
  'quantities_files': [File objects],   // ✅ Expected by backend  
  'drawings_files': [File objects],     // ✅ Expected by backend
  'ai_engine': 'auto',                  // ❌ NOT expected → Causes 422
  'language': 'en',                     // ❌ NOT expected → Causes 422
  'project_name': 'Project Analysis'    // ❌ NOT expected → Causes 422
}
```

The backend endpoint only accepts:
```python
@router.post("/unified")
async def analyze_files(
    technical_files: Optional[List[UploadFile]] = File(None),
    quantities_files: Optional[List[UploadFile]] = File(None),
    drawings_files: Optional[List[UploadFile]] = File(None)
):
```

**FastAPI's validation**: "I see fields `ai_engine`, `language`, `project_name` but they're not in my signature → 422"

## The Stack Trace Breakdown

```
AxiosError: Request failed with status code 422
    at Xh (https://stav-agent.onrender.com/assets/index-r4kooG97.js:35:1080)
    at XMLHttpRequest.V (https://stav-agent.onrender.com/assets/index-r4kooG97.js:35:5701)
    at Yl.request (https://stav-agent.onrender.com/assets/index-r4kooG97.js:37:2062)
    at async p1.post (https://stav-agent.onrender.com/assets/index-r4kooG97.js:38:9041)
    at async Object.L [as onClick] (https://stav-agent.onrender.com/assets/index-r4kooG97.js:38:9694)
```

**Translation**:
1. User clicked "Analyze" button (`onClick`)
2. Code called `apiClient.post()` to send files
3. Axios made XMLHttpRequest to backend
4. Backend returned 422 error
5. Axios threw AxiosError
6. Error bubbled up to user

## What the Backend Saw

```json
POST /api/v1/analysis/unified
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...

------WebKitFormBoundary...
Content-Disposition: form-data; name="technical_files"; filename="file.pdf"
...

------WebKitFormBoundary...
Content-Disposition: form-data; name="ai_engine"

auto
------WebKitFormBoundary... (more unexpected fields)
```

FastAPI validation:
1. ✅ Parsed `technical_files` → OK
2. ✅ Parsed `quantities_files` → OK  
3. ✅ Parsed `drawings_files` → OK
4. ❌ Found `ai_engine` → NOT in signature → **REJECT 422**

## Response Detail (from error.response.data.detail)

The `detail` array typically contains validation errors like:
```json
{
  "detail": [
    {
      "type": "extra_forbidden",
      "loc": ["body", "ai_engine"],
      "msg": "Extra inputs are not permitted",
      "input": "auto"
    }
  ]
}
```

This tells you:
- **type**: `extra_forbidden` - field not allowed
- **loc**: `["body", "ai_engine"]` - location of error
- **msg**: "Extra inputs are not permitted"
- **input**: "auto" - the value that was rejected

## The Fix

**Before** (Causes 422):
```typescript
formData.append('technical_files', file);
formData.append('quantities_files', file);
formData.append('drawings_files', file);
formData.append('ai_engine', 'auto');        // ❌ Remove this
formData.append('language', 'en');           // ❌ Remove this
formData.append('project_name', 'Project');  // ❌ Remove this
```

**After** (Works):
```typescript
formData.append('technical_files', file);
formData.append('quantities_files', file);
formData.append('drawings_files', file);
// No metadata fields - only what backend expects
```

## Verification

After fix, the request will be:
```
POST /api/v1/analysis/unified
Content-Type: multipart/form-data; boundary=...

------boundary...
Content-Disposition: form-data; name="technical_files"; filename="file.pdf"
...
------boundary--
```

Backend response:
```json
{
  "status": "success",
  "files": [...],
  "summary": {
    "total": 3,
    "successful": 3,
    "failed": 0
  }
}
```

Status: **200 OK** ✅

## Related HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 OK | Success | All files processed |
| 400 Bad Request | No files uploaded | Empty request |
| 422 Unprocessable Entity | Invalid request format | Extra/missing fields |
| 500 Internal Server Error | Server error | Processing failure |

## Key Lessons

1. **422 = Semantic Error**: Request format is correct, but content doesn't match API contract
2. **Check Endpoint Signature**: Always verify what parameters the backend expects
3. **FastAPI Strictness**: FastAPI validates strictly - no extra fields allowed
4. **Don't Set Content-Type Manually**: Let Axios/browser handle multipart/form-data
5. **Read Response Details**: `error.response.data.detail` tells you exactly what's wrong

## Summary

The 422 error occurred because the frontend was sending 3 metadata fields (`ai_engine`, `language`, `project_name`) that the backend endpoint doesn't accept. FastAPI's automatic validation rejected these extra fields with a 422 status code. The fix simply removes these fields, sending only what the backend expects.

**Result**: No more 422 errors! ✅
