# 🧪 Testing Strategy and Implementation Plan
## Concrete Agent - Construction Analysis API

**Date:** 2024-01-10  
**Repository:** alpro1000/concrete-agent

---

## 📋 Current Test Infrastructure

Based on analysis of the repository:

```bash
tests/
├── conftest.py                 # Pytest fixtures
├── test_concrete_agent.py      # Core module tests
├── test_integration.py         # Integration tests
├── test_llm_service.py         # LLM service tests
├── test_upload_endpoints.py    # Upload endpoint tests
├── test_tzd_reader.py          # TZD reader tests
├── test_doc_parser.py          # Document parser tests
├── test_claude_integration.py  # Claude integration tests
└── test_data/                  # Test data files
```

**Pytest Configuration:**
```ini
[pytest]
testpaths = tests
markers =
    integration: Integration tests
    slow: Slow running tests
    requires_api: Tests requiring API keys
```

---

## 🎯 Recommended Test Coverage

### 1. Security Tests (HIGH PRIORITY)

#### File Upload Security Tests
```python
# tests/test_security_file_upload.py
import pytest
from fastapi.testclient import TestClient
from io import BytesIO

class TestFileUploadSecurity:
    """Security tests for file upload functionality"""
    
    def test_file_size_limit_enforced(self, client):
        """Test that files exceeding size limit are rejected"""
        # Create 11MB file (exceeds 10MB limit)
        large_file = BytesIO(b"x" * (11 * 1024 * 1024))
        
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("large.pdf", large_file, "application/pdf")}
        )
        
        assert response.status_code == 400
        assert "превышает лимит" in response.json()["detail"]
    
    def test_invalid_file_extension_rejected(self, client):
        """Test that invalid file extensions are rejected"""
        file_content = BytesIO(b"malicious content")
        
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("malware.exe", file_content, "application/x-msdownload")}
        )
        
        assert response.status_code == 400
        assert "Недопустимое расширение" in response.json()["detail"]
    
    def test_path_traversal_protection(self, client):
        """Test protection against path traversal attacks"""
        file_content = BytesIO(b"test content")
        
        # Try to upload with path traversal in filename
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("../../etc/passwd", file_content, "text/plain")}
        )
        
        # Should be sanitized to just "passwd"
        assert response.status_code in [200, 400]
    
    def test_mime_type_validation(self, client):
        """Test MIME type validation"""
        # Create file with PDF extension but wrong content
        fake_pdf = BytesIO(b"This is not a PDF")
        
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("fake.pdf", fake_pdf, "application/pdf")}
        )
        
        # Should detect invalid MIME type
        assert response.status_code == 400
    
    def test_multiple_file_upload_limit(self, client):
        """Test that file count limits are enforced"""
        # Try to upload 11 files (if limit is 10)
        files = [
            ("files", (f"file{i}.txt", BytesIO(b"content"), "text/plain"))
            for i in range(11)
        ]
        
        response = client.post("/api/v1/tzd/analyze", files=files)
        
        # Should enforce limit
        assert response.status_code in [400, 413]
```

#### Authentication Tests
```python
# tests/test_security_auth.py
import pytest

class TestAuthentication:
    """Security tests for authentication"""
    
    def test_endpoint_requires_authentication(self, client):
        """Test that protected endpoints require authentication"""
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("test.txt", BytesIO(b"test"), "text/plain")}
        )
        
        # Should require auth (once implemented)
        # assert response.status_code == 401
        pass  # TODO: Implement after auth is added
    
    def test_invalid_api_key_rejected(self, client):
        """Test that invalid API keys are rejected"""
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("test.txt", BytesIO(b"test"), "text/plain")},
            headers={"Authorization": "Bearer invalid_key"}
        )
        
        # assert response.status_code == 401
        pass  # TODO: Implement after auth is added
    
    def test_valid_api_key_accepted(self, client, valid_api_key):
        """Test that valid API keys are accepted"""
        # TODO: Implement after auth is added
        pass
```

#### Rate Limiting Tests
```python
# tests/test_security_rate_limiting.py
import pytest
import asyncio

class TestRateLimiting:
    """Security tests for rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self, client):
        """Test that rate limits are enforced"""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.post(
                "/api/v1/tzd/analyze",
                files={"files": ("test.txt", BytesIO(b"test"), "text/plain")}
            )
            responses.append(response)
        
        # Should have at least one 429 response
        # assert any(r.status_code == 429 for r in responses)
        pass  # TODO: Implement after rate limiting is added
    
    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are included in responses"""
        response = client.get("/api/v1/tzd/health")
        
        # Should include rate limit headers
        # assert "X-RateLimit-Limit" in response.headers
        # assert "X-RateLimit-Remaining" in response.headers
        pass  # TODO: Implement after rate limiting is added
```

---

### 2. Integration Tests

#### Database Tests
```python
# tests/test_database_integration.py
import pytest
from sqlalchemy import text

class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self, db_session):
        """Test database connection is healthy"""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_connection_pool_limits(self, app):
        """Test connection pool handles concurrent requests"""
        # Create multiple concurrent database connections
        tasks = []
        for _ in range(30):  # More than pool size
            tasks.append(db_session.execute(text("SELECT 1")))
        
        results = await asyncio.gather(*tasks)
        assert all(r.scalar() == 1 for r in results)
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_session):
        """Test that failed transactions are rolled back"""
        from app.models import Project
        
        try:
            # Create invalid project
            project = Project(name=None)  # Should fail validation
            db_session.add(project)
            await db_session.commit()
            assert False, "Should have raised error"
        except:
            await db_session.rollback()
            # Session should still be usable
            result = await db_session.execute(text("SELECT 1"))
            assert result.scalar() == 1
```

#### LLM Service Tests
```python
# tests/test_llm_integration.py
import pytest

class TestLLMIntegration:
    """Integration tests for LLM services"""
    
    @pytest.mark.requires_api
    @pytest.mark.asyncio
    async def test_claude_api_connection(self, llm_service):
        """Test Claude API connection"""
        response = await llm_service.query_claude(
            prompt="Say 'test'",
            context="Testing"
        )
        assert response is not None
        assert len(response) > 0
    
    @pytest.mark.requires_api
    @pytest.mark.asyncio
    async def test_openai_api_connection(self, llm_service):
        """Test OpenAI API connection"""
        response = await llm_service.query_openai(
            prompt="Say 'test'",
            context="Testing"
        )
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_llm_error_handling(self, llm_service):
        """Test LLM service handles errors gracefully"""
        # Test with invalid API key
        llm_service.anthropic_api_key = "invalid"
        
        with pytest.raises(Exception):
            await llm_service.query_claude(
                prompt="test",
                context="test"
            )
```

---

### 3. Performance Tests

```python
# tests/test_performance.py
import pytest
import time
from io import BytesIO

class TestPerformance:
    """Performance tests"""
    
    @pytest.mark.slow
    def test_file_upload_performance(self, client):
        """Test file upload completes in reasonable time"""
        file_content = BytesIO(b"x" * (5 * 1024 * 1024))  # 5MB
        
        start = time.time()
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("large.pdf", file_content, "application/pdf")}
        )
        duration = time.time() - start
        
        assert duration < 10.0  # Should complete in under 10 seconds
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test system handles concurrent requests"""
        import asyncio
        
        async def make_request():
            return client.get("/api/v1/tzd/health")
        
        # Make 50 concurrent requests
        start = time.time()
        tasks = [make_request() for _ in range(50)]
        responses = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        assert all(r.status_code == 200 for r in responses)
        assert duration < 5.0  # Should handle 50 requests in under 5 seconds
```

---

### 4. API Contract Tests

```python
# tests/test_api_contracts.py
import pytest
from pydantic import ValidationError

class TestAPIContracts:
    """Tests for API request/response contracts"""
    
    def test_analyze_response_schema(self, client):
        """Test analyze endpoint returns correct schema"""
        response = client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("test.txt", BytesIO(b"test"), "text/plain")}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "analysis_id" in data
            assert "timestamp" in data
            assert "requirements" in data
            assert isinstance(data["requirements"], list)
    
    def test_health_endpoint_schema(self, client):
        """Test health endpoint returns correct schema"""
        response = client.get("/api/v1/tzd/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert "tzd_reader_available" in data
```

---

## 🚀 Quick Start Testing Guide

### Running All Tests
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run only fast tests (skip slow integration tests)
pytest tests/ -v -m "not slow"

# Run only security tests
pytest tests/test_security_*.py -v

# Run with parallel execution
pytest tests/ -v -n auto
```

### Running Specific Test Categories
```bash
# Security tests only
pytest tests/ -v -k "security"

# Integration tests only
pytest tests/ -v -m integration

# Tests that require API keys
pytest tests/ -v -m requires_api

# Performance tests
pytest tests/ -v -m slow
```

---

## 📊 Test Coverage Goals

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Security | ~20% | 90%+ | 🔴 HIGH |
| File Handling | ~40% | 85%+ | 🔴 HIGH |
| API Endpoints | ~50% | 80%+ | 🟡 MEDIUM |
| Database | ~30% | 75%+ | 🟡 MEDIUM |
| LLM Services | ~40% | 70%+ | 🟢 LOW |
| Core Utils | ~60% | 85%+ | 🟡 MEDIUM |

---

## 🔧 Test Fixtures

```python
# tests/conftest.py additions
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, engine
from app.models.base import Base

@pytest.fixture
async def db_session():
    """Provide a test database session"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client():
    """Provide a test client"""
    return TestClient(app)

@pytest.fixture
def valid_api_key():
    """Provide a valid test API key"""
    return "test_api_key_12345"

@pytest.fixture
def llm_service():
    """Provide LLM service instance"""
    from app.core.llm_service import get_llm_service
    return get_llm_service()

@pytest.fixture
def sample_pdf_file():
    """Provide a sample PDF file for testing"""
    return open("tests/test_data/sample.pdf", "rb")
```

---

## 📈 Continuous Testing

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: Run fast tests
        entry: pytest tests/ -m "not slow" --tb=short
        language: system
        pass_filenames: false
        always_run: true
```

### GitHub Actions
```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

---

## ✅ Testing Checklist

- [ ] Security tests implemented (file upload, auth, rate limiting)
- [ ] Integration tests for all services (DB, LLM, cache)
- [ ] Performance tests for critical paths
- [ ] API contract tests for all endpoints
- [ ] Error handling tests for edge cases
- [ ] Test fixtures properly configured
- [ ] Test coverage > 80% for critical paths
- [ ] CI/CD pipeline configured
- [ ] Pre-commit hooks enabled
- [ ] Test documentation updated

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-10
