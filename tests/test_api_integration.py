#!/usr/bin/env python3
"""
Test for the integrated API endpoint
test_api_integration.py

Tests the new POST /analyze/materials endpoint
"""

import asyncio
import httpx
import tempfile
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_files():
    """Create test files for API testing"""
    temp_dir = tempfile.mkdtemp()
    
    # Test document
    doc_path = os.path.join(temp_dir, "test_doc.txt")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("""
Projektová dokumentace
Použitý beton: C25/30 XC2 XF1
Použitá výztuž: Fe500 - 2500 kg
Okna PVC - 15 ks
Tepelná izolace XPS 100mm - 85.5 m2
Ocelový nosník IPE200 - 450 kg
Střešní krytina - tašky keramické - 125 m2
Těsnění EPDM - 45 m

MOSTNÍ OPĚRA ZE ŽELEZOBETONU C30/37
Objem betonu: 125.5 m3
Cena: 3500 Kč za m3
        """)
    
    # Test budget/smeta
    smeta_path = os.path.join(temp_dir, "test_smeta.txt")
    with open(smeta_path, "w", encoding="utf-8") as f:
        f.write("""
Položka 1: Beton C25/30 - 125.5 m3 - 3500 Kč/m3
Položka 2: Výztuž Fe500 - 2500 kg - 25 Kč/kg
Položka 3: Okna PVC - 15 ks - 3500 Kč/ks
        """)
    
    return temp_dir, doc_path, smeta_path

async def test_integrated_api():
    """Test the integrated materials analysis API"""
    logger.info("🚀 Testing integrated API endpoint")
    
    # Create test files
    temp_dir, doc_path, smeta_path = create_test_files()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test different material queries
            test_queries = [
                ("výztuž", "reinforcement"),
                ("okna", "windows"), 
                ("izolace", "insulation"),
                (None, "all materials")
            ]
            
            for query, description in test_queries:
                logger.info(f"📋 Testing query: {description} ({query})")
                
                # Prepare files
                files = {
                    "docs": ("test_doc.txt", open(doc_path, "rb"), "text/plain"),
                    "smeta": ("test_smeta.txt", open(smeta_path, "rb"), "text/plain")
                }
                
                # Prepare form data
                data = {
                    "use_claude": "false",
                    "claude_mode": "enhancement",
                    "language": "cz"
                }
                
                if query:
                    data["material_query"] = query
                
                try:
                    response = await client.post(
                        "http://localhost:8000/analyze/materials",
                        files=files,
                        data=data
                    )
                    
                    # Close files
                    for file_tuple in files.values():
                        if hasattr(file_tuple[1], 'close'):
                            file_tuple[1].close()
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Success for {description}:")
                        logger.info(f"   Concrete grades: {result.get('concrete_analysis', {}).get('total_grades', 0)}")
                        logger.info(f"   Volume: {result.get('volume_analysis', {}).get('total_volume_m3', 0)} m³")
                        logger.info(f"   Materials found: {result.get('material_analysis', {}).get('total_materials', 0)}")
                        logger.info(f"   Query: {result.get('request_parameters', {}).get('material_query', 'None')}")
                    else:
                        logger.error(f"❌ Error {response.status_code} for {description}: {response.text[:200]}")
                
                except Exception as e:
                    logger.error(f"❌ Request failed for {description}: {e}")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
    
    return True

if __name__ == "__main__":
    print("🚀 Starting integrated API test")
    print("Make sure the server is running on http://localhost:8000")
    
    success = asyncio.run(test_integrated_api())
    if success:
        print("✅ API integration test completed")
    else:
        print("❌ API integration test failed")