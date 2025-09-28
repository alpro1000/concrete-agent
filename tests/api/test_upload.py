# tests/api/test_upload.py
import pytest
import asyncio
import tempfile
import zipfile
import os
from httpx import AsyncClient
from app.main import app
from app.database import init_database


@pytest.fixture
async def client():
    """Create test client"""
    await init_database()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_project(client):
    """Create a test project"""
    project_data = {
        "name": "Upload Test Project",
        "description": "Project for testing file uploads",
        "metadata": {"type": "test"}
    }
    
    response = await client.post("/api/projects", json=project_data)
    return response.json()


class TestFileUpload:
    """Test file upload functionality"""
    
    async def test_single_file_upload(self, client, test_project):
        """Test uploading a single file"""
        project_id = test_project["id"]
        
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test concrete specification C30/37")
            temp_file = f.name
        
        try:
            # Upload file
            with open(temp_file, 'rb') as f:
                files = {"files": ("test_spec.txt", f, "text/plain")}
                response = await client.post(
                    f"/api/projects/{project_id}/upload",
                    files=files
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["project_id"] == project_id
            assert len(data["uploaded"]) == 1
            
            uploaded_file = data["uploaded"][0]
            assert uploaded_file["filename"] == "test_spec.txt"
            assert uploaded_file["file_type"] == "txt"
            assert uploaded_file["status"] == "new"
            assert "document_id" in uploaded_file
            assert "hash" in uploaded_file
            
        finally:
            os.unlink(temp_file)
    
    async def test_multiple_file_upload(self, client, test_project):
        """Test uploading multiple files"""
        project_id = test_project["id"]
        
        # Create test files
        files_data = [
            ("concrete_spec.txt", "Concrete grade C25/30 for foundations"),
            ("steel_spec.txt", "Steel grade S355 for structural elements"),
            ("materials.txt", "List of construction materials")
        ]
        
        temp_files = []
        
        try:
            # Create temporary files
            for filename, content in files_data:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(content)
                    temp_files.append((filename, f.name))
            
            # Upload files
            files_to_upload = []
            for filename, temp_path in temp_files:
                with open(temp_path, 'rb') as f:
                    files_to_upload.append(("files", (filename, f.read(), "text/plain")))
            
            response = await client.post(
                f"/api/projects/{project_id}/upload",
                files=files_to_upload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["project_id"] == project_id
            assert len(data["uploaded"]) == 3
            
            uploaded_filenames = [f["filename"] for f in data["uploaded"]]
            expected_filenames = [f[0] for f in files_data]
            
            for expected in expected_filenames:
                assert expected in uploaded_filenames
                
        finally:
            # Cleanup
            for _, temp_path in temp_files:
                os.unlink(temp_path)
    
    async def test_zip_file_upload(self, client, test_project):
        """Test uploading and extracting ZIP files"""
        project_id = test_project["id"]
        
        # Create ZIP file with test documents
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files to zip
            files_in_zip = {
                "foundation.txt": "Foundation concrete C30/37",
                "columns.txt": "Column concrete C35/45",
                "beams.txt": "Beam concrete C25/30"
            }
            
            for filename, content in files_in_zip.items():
                with open(os.path.join(temp_dir, filename), 'w') as f:
                    f.write(content)
            
            # Create ZIP file
            zip_path = os.path.join(temp_dir, "construction_docs.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for filename in files_in_zip.keys():
                    zipf.write(os.path.join(temp_dir, filename), filename)
            
            # Upload ZIP file
            with open(zip_path, 'rb') as f:
                files = {"files": ("construction_docs.zip", f, "application/zip")}
                response = await client.post(
                    f"/api/projects/{project_id}/upload",
                    files=files
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["project_id"] == project_id
            assert len(data["uploaded"]) == len(files_in_zip)
            
            # Check that all files from ZIP were extracted
            uploaded_filenames = [f["filename"] for f in data["uploaded"]]
            for expected_filename in files_in_zip.keys():
                assert expected_filename in uploaded_filenames
            
            # Check extraction status
            for uploaded_file in data["uploaded"]:
                assert uploaded_file["extraction_status"] == "extracted"
                assert "parent_zip" in uploaded_file
    
    async def test_invalid_project_upload(self, client):
        """Test uploading to non-existent project"""
        fake_project_id = "00000000-0000-0000-0000-000000000000"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {"files": ("test.txt", f, "text/plain")}
                response = await client.post(
                    f"/api/projects/{fake_project_id}/upload",
                    files=files
                )
            
            assert response.status_code == 404
            
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    # Simple test runner
    async def run_tests():
        try:
            await init_database()
            async with AsyncClient(app=app, base_url="http://test") as client:
                
                # Create test project
                project_data = {
                    "name": "Upload Test Project",
                    "description": "Project for testing file uploads",
                    "metadata": {"type": "test"}
                }
                response = await client.post("/api/projects", json=project_data)
                test_project = response.json()
                
                # Run tests
                tests = TestFileUpload()
                
                print("🧪 Running upload API tests...")
                
                await tests.test_single_file_upload(client, test_project)
                print("✅ test_single_file_upload passed")
                
                await tests.test_multiple_file_upload(client, test_project)
                print("✅ test_multiple_file_upload passed")
                
                await tests.test_zip_file_upload(client, test_project)
                print("✅ test_zip_file_upload passed")
                
                await tests.test_invalid_project_upload(client)
                print("✅ test_invalid_project_upload passed")
                
                print("🎉 All upload tests passed!")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    # Run if called directly
    asyncio.run(run_tests())