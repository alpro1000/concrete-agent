# 🛠️ Implementation Guide: Priority Security & Architecture Fixes
## Concrete Agent - Step-by-Step Remediation Plan

**Date:** 2024-01-10  
**Repository:** alpro1000/concrete-agent

---

## 🎯 Overview

This guide provides concrete, copy-paste ready implementations for the top 15 security and architecture improvements identified in the security analysis.

---

## 🔴 CRITICAL PRIORITY (Implement Immediately)

### 1. Add Authentication System

**File:** `app/core/auth.py` (NEW)

```python
"""
Authentication and authorization middleware
"""
import os
import secrets
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthService:
    """Service for API authentication"""
    
    def __init__(self):
        # Load API keys from environment
        self.api_keys = self._load_api_keys()
        
        if not self.api_keys:
            logger.warning("⚠️ No API keys configured - authentication disabled!")
    
    def _load_api_keys(self) -> set:
        """Load API keys from environment variable"""
        keys_str = os.getenv("API_KEYS", "")
        if not keys_str:
            return set()
        
        # Support comma-separated list of keys
        keys = {key.strip() for key in keys_str.split(",") if key.strip()}
        return keys
    
    def validate_key(self, api_key: str) -> bool:
        """Validate an API key"""
        if not self.api_keys:
            # No keys configured - allow all (development mode)
            return True
        
        return api_key in self.api_keys
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random API key"""
        return f"sk_{secrets.token_urlsafe(32)}"


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get or create auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Dependency for API key authentication
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(verify_api_key)])
        async def protected_endpoint():
            pass
    """
    auth_service = get_auth_service()
    
    if not auth_service.validate_key(credentials.credentials):
        logger.warning(f"Invalid API key attempt: {credentials.credentials[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


async def optional_verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(
        HTTPBearer(auto_error=False)
    )
) -> Optional[str]:
    """
    Optional API key verification - allows both authenticated and anonymous access
    """
    if credentials is None:
        return None
    
    auth_service = get_auth_service()
    if auth_service.validate_key(credentials.credentials):
        return credentials.credentials
    
    return None
```

**Update:** `.env.template`

```bash
# API Authentication
# Comma-separated list of valid API keys
API_KEYS=sk_your_api_key_here,sk_another_key_here

# Generate new keys with: python -c "import secrets; print(f'sk_{secrets.token_urlsafe(32)}')"
```

**Update:** `app/routers/tzd_router.py`

```python
from fastapi import Depends
from app.core.auth import verify_api_key

# Add to protected endpoints
@router.post("/analyze", response_model=TZDAnalysisResponse, dependencies=[Depends(verify_api_key)])
async def analyze_tzd_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    ai_engine: str = Form(default="auto"),
    project_context: Optional[str] = Form(None)
):
    # ... existing code
```

---

### 2. Implement Rate Limiting

**Install dependency:**
```bash
pip install slowapi
```

**Update:** `requirements.txt`
```
slowapi==0.1.9
```

**File:** `app/core/rate_limiter.py` (NEW)

```python
"""
Rate limiting configuration
"""
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour"],  # Default limit for all endpoints
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Use Redis if available
    strategy="fixed-window",
    headers_enabled=True,
)


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded"""
    logger.warning(
        f"Rate limit exceeded for {get_remote_address(request)} "
        f"on {request.url.path}"
    )
    
    return Response(
        content='{"detail": "Превышен лимит запросов. Пожалуйста, повторите позже."}',
        status_code=429,
        headers={
            "Content-Type": "application/json",
            "Retry-After": str(exc.retry_after) if hasattr(exc, 'retry_after') else "60",
        }
    )


def setup_rate_limiting(app):
    """Setup rate limiting for FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
    logger.info("✅ Rate limiting enabled")
```

**Update:** `app/main.py`

```python
from app.core.rate_limiter import setup_rate_limiting, limiter

# After creating app
app = FastAPI(...)

# Add rate limiting
setup_rate_limiting(app)

# ... rest of code
```

**Update:** `app/routers/tzd_router.py`

```python
from app.core.rate_limiter import limiter
from fastapi import Request

# Add rate limit to analyze endpoint
@router.post("/analyze", response_model=TZDAnalysisResponse)
@limiter.limit("5/minute")  # 5 requests per minute
async def analyze_tzd_documents(
    request: Request,  # Required by limiter
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    # ... rest of parameters
):
    # ... existing code

# Health endpoint - higher limit
@router.get("/health")
@limiter.limit("30/minute")
async def tzd_health(request: Request):
    # ... existing code
```

---

### 3. Fix Streaming File Upload

**Update:** `app/routers/tzd_router.py`

```python
import aiofiles
import asyncio
from pathlib import Path

async def save_file_safe(
    file: UploadFile,
    file_path: str,
    max_size: int = 10 * 1024 * 1024
) -> int:
    """
    Safely save uploaded file with streaming and size limit
    
    Args:
        file: Uploaded file
        file_path: Destination path
        max_size: Maximum file size in bytes
        
    Returns:
        File size in bytes
        
    Raises:
        HTTPException: If file exceeds size limit
    """
    size = 0
    chunk_size = 8192  # 8KB chunks
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                size += len(chunk)
                
                # Check size limit
                if size > max_size:
                    # Clean up partial file
                    await f.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Файл превышает лимит {max_size / 1024 / 1024:.1f}MB"
                    )
                
                await f.write(chunk)
        
        logger.info(f"File saved successfully: {Path(file_path).name} ({size:,} bytes)")
        return size
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error saving file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {str(e)}")


# Update analyze endpoint
@router.post("/analyze", response_model=TZDAnalysisResponse)
async def analyze_tzd_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    ai_engine: str = Form(default="auto"),
    project_context: Optional[str] = Form(None)
):
    # ... validation code
    
    temp_dir = tempfile.mkdtemp(prefix="tzd_secure_")
    file_paths = []
    
    try:
        validator = FileSecurityValidator()
        
        for file in files:
            if not file.filename:
                continue
            
            # Validate extension
            try:
                validator.validate_file_extension(file.filename)
            except SecurityError as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            # Save file with streaming
            safe_filename = Path(file.filename).name
            file_path = os.path.join(temp_dir, safe_filename)
            
            # Use async streaming save
            await save_file_safe(file, file_path, max_size=10 * 1024 * 1024)
            
            # Validate saved file
            try:
                validator.validate_all(file_path, base_dir=temp_dir)
            except SecurityError as e:
                os.remove(file_path)
                raise HTTPException(status_code=400, detail=str(e))
            
            file_paths.append(file_path)
        
        # ... rest of existing code
```

---

### 4. Add API Key Validation at Startup

**File:** `app/core/startup.py` (NEW)

```python
"""
Startup validation and configuration checks
"""
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class StartupValidationError(Exception):
    """Exception raised when startup validation fails"""
    pass


def validate_environment_variables() -> Dict[str, bool]:
    """
    Validate required environment variables are set
    
    Returns:
        Dictionary of validation results
    """
    validations = {}
    
    # Required variables
    required = {
        "ANTHROPIC_API_KEY": "Claude API integration",
        "OPENAI_API_KEY": "OpenAI API integration",
    }
    
    # Optional but recommended
    recommended = {
        "API_KEYS": "API authentication",
        "DATABASE_URL": "Database connection",
        "REDIS_URL": "Caching and rate limiting",
        "SENTRY_DSN": "Error tracking",
    }
    
    # Check required
    for var, purpose in required.items():
        value = os.getenv(var)
        is_set = bool(value and len(value) > 10)
        validations[var] = is_set
        
        if not is_set:
            logger.warning(f"⚠️ Required variable {var} not set ({purpose})")
    
    # Check recommended
    for var, purpose in recommended.items():
        value = os.getenv(var)
        is_set = bool(value)
        
        if not is_set:
            logger.info(f"ℹ️ Recommended variable {var} not set ({purpose})")
    
    return validations


def validate_api_keys():
    """Validate API keys are properly formatted"""
    # Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key and not anthropic_key.startswith("sk-ant-"):
        logger.warning("⚠️ ANTHROPIC_API_KEY may be invalid (should start with 'sk-ant-')")
    
    # OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key and not openai_key.startswith("sk-"):
        logger.warning("⚠️ OPENAI_API_KEY may be invalid (should start with 'sk-')")


def validate_directories():
    """Validate required directories exist"""
    directories = ["uploads", "logs", "outputs", "storage"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"✅ Created directory: {directory}")
        else:
            # Check write permissions
            test_file = os.path.join(directory, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                logger.debug(f"✅ Directory writable: {directory}")
            except Exception as e:
                raise StartupValidationError(
                    f"Directory {directory} is not writable: {e}"
                )


def validate_database_url():
    """Validate database URL is properly configured"""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        logger.warning("⚠️ DATABASE_URL not set, using SQLite")
        return
    
    # Check PostgreSQL URL format
    if db_url.startswith("postgresql://"):
        logger.info("✅ PostgreSQL database configured")
    elif db_url.startswith("sqlite"):
        logger.info("ℹ️ Using SQLite database (not recommended for production)")
    else:
        logger.warning(f"⚠️ Unknown database type in DATABASE_URL")


def run_startup_validations():
    """
    Run all startup validations
    
    Raises:
        StartupValidationError: If critical validations fail
    """
    logger.info("🔍 Running startup validations...")
    
    # Validate environment
    env_validations = validate_environment_variables()
    
    # Validate API keys
    validate_api_keys()
    
    # Validate directories
    validate_directories()
    
    # Validate database
    validate_database_url()
    
    # Check critical failures
    critical_missing = [
        var for var, is_set in env_validations.items()
        if not is_set
    ]
    
    if critical_missing:
        logger.error(
            f"❌ Critical environment variables missing: {', '.join(critical_missing)}"
        )
        logger.error("Application may not function correctly!")
        # Don't raise exception - allow app to start but log warnings
    else:
        logger.info("✅ All startup validations passed")
```

**Update:** `app/main.py`

```python
from app.core.startup import run_startup_validations

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Construction Analysis API starting...")
    
    # Run validations
    try:
        run_startup_validations()
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        # Continue anyway but log error
    
    # ... rest of startup code
```

---

## 🟡 HIGH PRIORITY (1-2 Weeks)

### 5. Refactor to Service Layer Architecture

**File:** `app/services/file_service.py` (NEW)

```python
"""
File handling service - business logic for file operations
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
import aiofiles
import logging

from agents.tzd_reader.security import FileSecurityValidator, SecurityError

logger = logging.getLogger(__name__)


class FileService:
    """Service for file handling operations"""
    
    def __init__(self):
        self.validator = FileSecurityValidator()
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    async def save_uploaded_file(
        self,
        file: UploadFile,
        destination_dir: str,
        validate: bool = True
    ) -> str:
        """
        Save uploaded file with validation
        
        Args:
            file: Uploaded file
            destination_dir: Directory to save file
            validate: Whether to run security validation
            
        Returns:
            Path to saved file
            
        Raises:
            SecurityError: If validation fails
        """
        # Sanitize filename
        safe_filename = Path(file.filename).name
        file_path = os.path.join(destination_dir, safe_filename)
        
        # Validate extension before saving
        if validate:
            self.validator.validate_file_extension(safe_filename)
        
        # Save with streaming
        size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):
                size += len(chunk)
                if size > self.max_file_size:
                    await f.close()
                    os.remove(file_path)
                    raise SecurityError(
                        f"File too large: {size:,} bytes "
                        f"(max: {self.max_file_size:,} bytes)"
                    )
                await f.write(chunk)
        
        # Validate saved file
        if validate:
            try:
                self.validator.validate_all(file_path, base_dir=destination_dir)
            except SecurityError as e:
                os.remove(file_path)
                raise
        
        logger.info(f"File saved: {safe_filename} ({size:,} bytes)")
        return file_path
    
    async def save_multiple_files(
        self,
        files: List[UploadFile],
        destination_dir: Optional[str] = None
    ) -> List[str]:
        """
        Save multiple uploaded files
        
        Args:
            files: List of uploaded files
            destination_dir: Directory to save files (creates temp if None)
            
        Returns:
            List of saved file paths
        """
        if destination_dir is None:
            destination_dir = tempfile.mkdtemp(prefix="files_")
        
        saved_paths = []
        
        try:
            for file in files:
                if not file.filename:
                    continue
                
                file_path = await self.save_uploaded_file(
                    file,
                    destination_dir,
                    validate=True
                )
                saved_paths.append(file_path)
            
            return saved_paths
            
        except Exception as e:
            # Cleanup on error
            for path in saved_paths:
                if os.path.exists(path):
                    os.remove(path)
            raise
    
    @staticmethod
    def cleanup_directory(directory: str, force: bool = False):
        """
        Safely cleanup a directory
        
        Args:
            directory: Directory to cleanup
            force: If True, cleanup even if not in /tmp
        """
        if not os.path.exists(directory):
            return
        
        # Safety check - only cleanup /tmp directories unless forced
        if not force and not directory.startswith('/tmp/'):
            logger.warning(f"Refusing to cleanup non-temp directory: {directory}")
            return
        
        try:
            shutil.rmtree(directory)
            logger.info(f"Cleaned up directory: {directory}")
        except Exception as e:
            logger.error(f"Failed to cleanup {directory}: {e}")
```

**File:** `app/services/tzd_service.py` (NEW)

```python
"""
TZD analysis service - business logic
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TZDService:
    """Service for TZD document analysis"""
    
    def __init__(self):
        try:
            from agents.tzd_reader.agent import tzd_reader
            self.tzd_reader = tzd_reader
            self.available = True
        except ImportError:
            logger.warning("TZD Reader not available")
            self.available = False
            self.tzd_reader = None
    
    async def analyze_documents(
        self,
        file_paths: List[str],
        ai_engine: str = "auto",
        project_context: Optional[str] = None,
        base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze TZD documents
        
        Args:
            file_paths: List of file paths to analyze
            ai_engine: AI engine to use (gpt, claude, auto)
            project_context: Optional project context
            base_dir: Base directory for file operations
            
        Returns:
            Analysis results
        """
        if not self.available:
            return {
                "success": False,
                "error": "TZD Reader not available",
                "analysis_id": "error",
                "timestamp": datetime.now().isoformat()
            }
        
        logger.info(
            f"Starting TZD analysis: {len(file_paths)} files, "
            f"engine={ai_engine}"
        )
        
        try:
            # Call TZD reader
            result = self.tzd_reader(
                files=file_paths,
                engine=ai_engine,
                base_dir=base_dir
            )
            
            # Enrich result
            result["success"] = True
            result["llm_orchestrator_used"] = True
            
            if "timestamp" not in result:
                result["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"TZD analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"TZD analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "analysis_id": "error",
                "timestamp": datetime.now().isoformat()
            }
```

**Update:** `app/routers/tzd_router.py`

```python
from fastapi import Depends
from app.services.file_service import FileService
from app.services.tzd_service import TZDService

# Dependency injection
def get_file_service() -> FileService:
    return FileService()

def get_tzd_service() -> TZDService:
    return TZDService()

# Simplified router
@router.post("/analyze", response_model=TZDAnalysisResponse)
async def analyze_tzd_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    ai_engine: str = Form(default="auto"),
    project_context: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service),
    tzd_service: TZDService = Depends(get_tzd_service)
):
    """Analyze TZD documents - now with service layer"""
    
    temp_dir = None
    
    try:
        # Save files using service
        file_paths = await file_service.save_multiple_files(files)
        temp_dir = os.path.dirname(file_paths[0])
        
        # Analyze using service
        result = await tzd_service.analyze_documents(
            file_paths=file_paths,
            ai_engine=ai_engine,
            project_context=project_context,
            base_dir=temp_dir
        )
        
        # Cache result
        analysis_id = result.get("analysis_id", f"tzd_{datetime.now().strftime('%H%M%S')}")
        analysis_cache[analysis_id] = result
        
        # Schedule cleanup
        if temp_dir:
            background_tasks.add_task(file_service.cleanup_directory, temp_dir)
        
        return TZDAnalysisResponse(**result)
        
    except SecurityError as e:
        if temp_dir:
            file_service.cleanup_directory(temp_dir)
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        if temp_dir:
            file_service.cleanup_directory(temp_dir)
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 📊 Implementation Progress Tracker

| Priority | Item | Status | Est. Time |
|----------|------|--------|-----------|
| 🔴 Critical | 1. Authentication | ⬜ Not Started | 2 hours |
| 🔴 Critical | 2. Rate Limiting | ⬜ Not Started | 1 hour |
| 🔴 Critical | 3. Streaming Upload | ⬜ Not Started | 3 hours |
| 🔴 Critical | 4. API Key Validation | ⬜ Not Started | 1 hour |
| 🟡 High | 5. Service Layer | ⬜ Not Started | 1 day |
| 🟡 High | 6. Monitoring | ⬜ Not Started | 1 day |
| 🟡 High | 7. Redis Caching | ⬜ Not Started | 2 hours |
| 🟡 High | 8. Async Operations | ⬜ Not Started | 2 hours |

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-10
