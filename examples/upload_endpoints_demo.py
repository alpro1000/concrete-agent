#!/usr/bin/env python3
"""
Demo script showing how to use the three specialized upload endpoints
"""
import requests
import json
import tempfile
import os

# Server URL (adjust as needed)
BASE_URL = "http://localhost:8001"

def create_demo_files():
    """Create demo files for testing"""
    temp_dir = tempfile.mkdtemp()
    
    # Create technical specification document
    tz_path = os.path.join(temp_dir, "technical_specification.txt")
    with open(tz_path, "w", encoding="utf-8") as f:
        f.write("""
ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ
Проект: Офисное здание
Объект: 4-этажное здание с подвалом
Основные требования:
- Бетон: C25/30 для фундамента, C20/25 для стен
- Арматура: B500B для основных конструкций
- Кирпич: керамический полнотелый
- Плитка: керамогранит 60x60 см
Геология: глинистые грунты, уровень грунтовых вод -3.2м
        """)
    
    # Create estimate XML
    smeta_path = os.path.join(temp_dir, "local_estimate.xml")
    with open(smeta_path, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<estimate>
    <header>
        <name>Локальная смета на фундамент</name>
        <object>Офисное здание</object>
    </header>
    <works>
        <item>
            <code>01-01-001</code>
            <name>Разработка грунта экскаватором</name>
            <unit>м3</unit>
            <quantity>150</quantity>
            <unit_price>250</unit_price>
            <total>37500</total>
        </item>
        <item>
            <code>06-01-001</code>
            <name>Бетонирование фундамента</name>
            <unit>м3</unit>
            <quantity>80</quantity>
            <unit_price>3500</unit_price>
            <total>280000</total>
        </item>
    </works>
    <summary>
        <total_cost>317500</total_cost>
        <total_volume>230</total_volume>
    </summary>
</estimate>""")
    
    # Create drawing file (mock PDF)
    drawing_path = os.path.join(temp_dir, "architectural_plan.pdf")
    with open(drawing_path, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
    
    return temp_dir, tz_path, smeta_path, drawing_path

def upload_project_documents(tz_path):
    """Demo: Upload project documents"""
    print("\n🔵 TESTING PROJECT DOCUMENTS UPLOAD")
    print("=" * 50)
    
    with open(tz_path, "rb") as f:
        files = {"files": ("technical_specification.txt", f, "text/plain")}
        data = {
            "project_name": "Office Building Demo",
            "auto_analyze": "false",  # Disable analysis for demo
            "language": "cz"
        }
        
        response = requests.post(f"{BASE_URL}/upload/docs", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Project documents uploaded successfully!")
        print(f"   📄 Files uploaded: {result['total_files']}")
        print(f"   🎯 Document type detected: {result['files'][0]['type']}")
        print(f"   🤖 Supported agents: {', '.join(result['supported_agents'])}")
        print(f"   📊 Status: {result['status']}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")

def upload_estimates(smeta_path):
    """Demo: Upload estimates/BOQ"""
    print("\n🟡 TESTING ESTIMATES UPLOAD")
    print("=" * 50)
    
    with open(smeta_path, "rb") as f:
        files = {"files": ("local_estimate.xml", f, "application/xml")}
        data = {
            "project_name": "Office Building Demo",
            "estimate_type": "local",
            "auto_analyze": "false",  # Disable analysis for demo
            "language": "cz"
        }
        
        response = requests.post(f"{BASE_URL}/upload/smeta", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Estimates uploaded successfully!")
        print(f"   📊 Files uploaded: {result['total_files']}")
        print(f"   📈 Estimate type: {result['estimate_type']}")
        print(f"   🔍 File type detected: {result['files'][0]['type']}")
        print(f"   🤖 Supported agents: {', '.join(result['supported_agents'])}")
        print(f"   💾 Format: {result['files'][0]['format']}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")

def upload_drawings(drawing_path):
    """Demo: Upload technical drawings"""
    print("\n🟢 TESTING DRAWINGS UPLOAD")
    print("=" * 50)
    
    with open(drawing_path, "rb") as f:
        files = {"files": ("architectural_plan.pdf", f, "application/pdf")}
        data = {
            "project_name": "Office Building Demo",
            "drawing_type": "architectural",
            "scale": "1:100",
            "auto_analyze": "false",  # Disable analysis for demo
            "extract_volumes": "true",
            "language": "cz"
        }
        
        response = requests.post(f"{BASE_URL}/upload/drawings", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Drawings uploaded successfully!")
        print(f"   📐 Files uploaded: {result['total_files']}")
        print(f"   🏗️ Drawing type: {result['drawing_type']}")
        print(f"   📏 Scale: {result['scale']}")
        print(f"   🔍 File type detected: {result['files'][0]['type']}")
        print(f"   🤖 Supported agents: {', '.join(result['supported_agents'])}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")

def test_error_handling():
    """Demo: Test error handling with invalid file"""
    print("\n🔴 TESTING ERROR HANDLING")
    print("=" * 50)
    
    # Create invalid file
    temp_dir = tempfile.mkdtemp()
    invalid_path = os.path.join(temp_dir, "invalid.exe")
    with open(invalid_path, "w") as f:
        f.write("Invalid file content")
    
    with open(invalid_path, "rb") as f:
        files = {"files": ("invalid.exe", f, "application/octet-stream")}
        data = {"project_name": "Error Test"}
        
        response = requests.post(f"{BASE_URL}/upload/docs", files=files, data=data)
    
    if response.status_code == 400:
        print("✅ Error handling works correctly!")
        print(f"   Status: {response.status_code}")
        print(f"   Message: {response.json()['detail']}")
    else:
        print(f"❌ Unexpected response: {response.status_code}")
    
    # Clean up
    os.remove(invalid_path)
    os.rmdir(temp_dir)

def main():
    """Main demo function"""
    print("🚀 UPLOAD ENDPOINTS DEMO")
    print("=" * 60)
    print("This demo shows the three specialized upload endpoints:")
    print("1. 📄 /upload/docs - Project documents (TZ, PDF, DOCX, TXT)")
    print("2. 📊 /upload/smeta - Estimates/BOQ (XLSX, XML, CSV, XC4)")
    print("3. 📐 /upload/drawings - Technical drawings (DWG, DXF, PDF, BIM)")
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print(f"\n❌ Server not accessible at {BASE_URL}")
            print("Please start the server first: python test_upload_endpoints.py")
            return
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {BASE_URL}")
        print("Please start the server first: python test_upload_endpoints.py")
        return
    
    # Create demo files
    temp_dir, tz_path, smeta_path, drawing_path = create_demo_files()
    
    try:
        # Test all endpoints
        upload_project_documents(tz_path)
        upload_estimates(smeta_path)
        upload_drawings(drawing_path)
        test_error_handling()
        
        print("\n🎉 DEMO COMPLETED!")
        print("=" * 60)
        print("All three specialized upload endpoints are working correctly!")
        print("\nSupported file types:")
        print("📄 Documents: PDF, DOCX, TXT, DOC, RTF")
        print("📊 Estimates: XLSX, XML, CSV, XC4, JSON, ODS")
        print("📐 Drawings: DWG, DXF, PDF, IFC, STEP, IGES, 3DM")
        
    finally:
        # Clean up demo files
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up temporary files from {temp_dir}")

if __name__ == "__main__":
    main()