# tests/api/test_projects.py
import pytest
import asyncio
import sys
import os
sys.path.append('/home/runner/work/concrete-agent/concrete-agent')

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.database import get_db, init_database
import tempfile


@pytest.fixture
async def client():
    """Create test client"""
    # Initialize database
    await init_database()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_project(client):
    """Create a test project"""
    project_data = {
        "name": "Test Construction Project",
        "description": "A test project for API testing",
        "metadata": {"location": "Prague", "type": "residential"}
    }
    
    response = await client.post("/api/projects", json=project_data)
    assert response.status_code == 200
    return response.json()


class TestProjects:
    """Test project management endpoints"""
    
    async def test_create_project(self, client):
        """Test project creation"""
        project_data = {
            "name": "New Construction Project",
            "description": "Testing project creation",
            "metadata": {"type": "commercial"}
        }
        
        response = await client.post("/api/projects", json=project_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert data["metadata"]["type"] == "commercial"
        assert "id" in data
        assert "created_at" in data
    
    async def test_list_projects(self, client, test_project):
        """Test listing projects"""
        response = await client.get("/api/projects")
        assert response.status_code == 200
        
        projects = response.json()
        assert isinstance(projects, list)
        assert len(projects) >= 1
        
        # Check if our test project is in the list
        project_names = [p["name"] for p in projects]
        assert test_project["name"] in project_names
    
    async def test_get_project(self, client, test_project):
        """Test getting specific project"""
        project_id = test_project["id"]
        
        response = await client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == test_project["name"]
    
    async def test_get_nonexistent_project(self, client):
        """Test getting non-existent project"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.get(f"/api/projects/{fake_id}")
        assert response.status_code == 404


if __name__ == "__main__":
    # Simple test runner
    async def run_tests():
        client_instance = None
        test_project_instance = None
        
        try:
            # Setup
            await init_database()
            async with AsyncClient(app=app, base_url="http://test") as client_instance:
                
                # Create test project
                project_data = {
                    "name": "Test Construction Project",
                    "description": "A test project for API testing", 
                    "metadata": {"location": "Prague", "type": "residential"}
                }
                response = await client_instance.post("/api/projects", json=project_data)
                test_project_instance = response.json()
                
                # Run tests
                tests = TestProjects()
                
                print("🧪 Running project API tests...")
                
                await tests.test_create_project(client_instance)
                print("✅ test_create_project passed")
                
                await tests.test_list_projects(client_instance, test_project_instance)
                print("✅ test_list_projects passed")
                
                await tests.test_get_project(client_instance, test_project_instance)
                print("✅ test_get_project passed")
                
                await tests.test_get_nonexistent_project(client_instance)
                print("✅ test_get_nonexistent_project passed")
                
                print("🎉 All tests passed!")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    # Run if called directly
    asyncio.run(run_tests())