# FastAPI File Upload Patterns

## Problem: Optional File Upload Fields Showing as Text Fields in Swagger UI

### Issue Description
When using `Optional[UploadFile] = File(None)` in FastAPI endpoints, the Swagger UI renders the field as a text input instead of a file upload button.

### Root Cause
FastAPI generates different OpenAPI schemas for optional vs required file uploads:

- ❌ **Problematic**: `Optional[UploadFile] = File(None)`
  - Generates: `anyOf: [{"type": "string", "format": "binary"}, {"type": "null"}]`
  - Result: Swagger UI renders as text field

- ✅ **Correct**: `UploadFile = File(...)`
  - Generates: `{"type": "string", "format": "binary"}`
  - Result: Swagger UI renders as file upload button

### Solution Pattern

#### Before (Problematic)
```python
@router.post("/endpoint")
async def endpoint(
    docs: List[UploadFile] = File(...),
    optional_file: Optional[UploadFile] = File(None, description="Optional file")
):
    if optional_file:
        # Process file
        pass
```

#### After (Fixed)
```python
@router.post("/endpoint") 
async def endpoint(
    docs: List[UploadFile] = File(...),
    optional_file: UploadFile = File(..., description="Optional file (upload empty file if none)")
):
    # Handle empty files in backend logic
    if optional_file and optional_file.filename and optional_file.size > 0:
        # Process actual file
        pass
    else:
        # Handle case when no file provided (empty file uploaded)
        pass
```

### Backend Logic for Optional Files

```python
# Check if a meaningful file was uploaded
def is_file_provided(file: UploadFile) -> bool:
    return file and file.filename and file.size > 0

# Usage in endpoint
smeta_provided = is_file_provided(smeta)
if smeta_provided:
    # Process the smeta file
    smeta_path = save_file(smeta)
else:
    # Continue without smeta
    smeta_path = None
```

### User Experience
- **UI**: Users see a proper file upload button with browse functionality
- **UX**: Clear instructions in description field guide users on handling optional files
- **Backend**: Robust handling of both real files and empty placeholder files

### Applied Fix Location
- **File**: `routers/analyze_materials.py`
- **Endpoint**: `/materials`
- **Parameter**: `smeta`
- **Status**: ✅ Fixed - now shows file upload button in Swagger UI

### Testing
Use this pattern for all optional file uploads to ensure consistent UI behavior across all endpoints.