# Changelog

## [Unreleased]

### Fixed
- **422 Unprocessable Entity Error**: Fixed file upload issue by removing manual `Content-Type` header setting in `frontend/src/api/client.ts`. The browser/Axios now automatically sets the correct `Content-Type: multipart/form-data` header with the required boundary parameter.

## Changes Made

### frontend/src/api/client.ts
- Removed manual `Content-Type: multipart/form-data` header from `uploadFiles` function
- Axios now handles Content-Type header automatically with proper boundary

### Why This Fixes the 422 Error

The FastAPI backend expects files to be sent as:
```python
technical_files: Optional[List[UploadFile]]
quantities_files: Optional[List[UploadFile]]
drawings_files: Optional[List[UploadFile]]
```

When the frontend manually set `Content-Type: multipart/form-data` without the boundary parameter, the server couldn't parse the multipart form data correctly, resulting in the error:
```
"Input should be a valid list", "loc":["body","technical_files"]
```

By letting Axios handle the Content-Type header automatically, it includes the boundary parameter:
```
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
```

This allows FastAPI to correctly parse the multipart form data and receive the files as lists.

## Testing

The fix has been verified:
- ✅ Frontend builds successfully
- ✅ Backend endpoint accepts file arrays correctly
- ✅ No new linting errors introduced
