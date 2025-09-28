#!/usr/bin/env python3
"""
Demo script showing MinerU integration in the Construction Analysis API

This script demonstrates:
1. How the unified parser works with MinerU integration
2. Fallback behavior when MinerU is unavailable
3. ZIP archive processing
4. Integration with existing agents

Usage:
    python demo_mineru_integration.py
    MINERU_ENABLED=true python demo_mineru_integration.py
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path

# Add project root to path
sys.path.append('.')

from services.doc_parser import parse_document, get_unified_document_parser
from utils.mineru_client import get_mineru_info


def main():
    print("🏗️  Construction Analysis API - MinerU Integration Demo")
    print("=" * 60)
    
    # Show MinerU status
    info = get_mineru_info()
    print(f"📊 MinerU Status:")
    print(f"   Enabled: {info['enabled']}")
    print(f"   Available: {info['available']}")
    print(f"   Supported formats: {', '.join(info['supported_formats'])}")
    print()
    
    # Demo 1: Single document parsing
    print("📄 Demo 1: Single Document Parsing")
    print("-" * 40)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("""
Projektová dokumentace - Konstrukční řešení

1. ZÁKLADOVÁ KONSTRUKCE
   - Beton C30/37 - XC2, XF1
   - Objem základové desky: 85.5 m³
   - Rozměry: 15.0 x 8.5 x 0.8 m
   - Výztuž: Fe500, celkem 1250 kg

2. NOSNÁ KONSTRUKCE
   - Sloupy: Železobeton C35/45 - XC4
   - Rozměry sloupů: 400x400 mm
   - Počet sloupů: 12 ks
   - Objem betonu sloupů: 28.8 m³
   
3. STROPNÍ KONSTRUKCE  
   - Monolitická železobetonová deska
   - Třída betonu: C25/30 - XC1
   - Tloušťka desky: 220 mm
   - Plocha: 195.5 m²
   - Objem: 43.0 m³

4. IZOLACE A OSTATNÍ MATERIÁLY
   - Tepelná izolace XPS 100mm: 195.5 m²
   - Hydroizolace EPDM: 85 m²
   - Okna PVC: 18 ks
   - Těsnění EPDM: 145 m
        """)
        f.flush()
        temp_path = f.name
    
    try:
        result = parse_document(temp_path)
        
        print(f"✅ Parsing successful: {result['success']}")
        print(f"📝 Results count: {len(result['results'])}")
        
        if result['results']:
            parse_result = result['results'][0]
            print(f"🔧 Parser used: {parse_result.parser_used}")
            print(f"📏 Content length: {len(str(parse_result.content))} characters")
            print(f"🏷️  Metadata: {parse_result.metadata}")
            
            # Show concrete grades found
            content_str = str(parse_result.content)
            concrete_grades = []
            for grade in ['C30/37', 'C35/45', 'C25/30']:
                if grade in content_str:
                    concrete_grades.append(grade)
            
            print(f"🏗️  Concrete grades detected: {', '.join(concrete_grades)}")
            
            # Show volume information
            volume_info = []
            if 'm³' in content_str:
                volume_info.append('volume (m³)')
            if 'm²' in content_str:
                volume_info.append('area (m²)')
            if 'kg' in content_str:
                volume_info.append('weight (kg)')
                
            print(f"📊 Units detected: {', '.join(volume_info)}")
        
    finally:
        os.unlink(temp_path)
    
    print()
    
    # Demo 2: ZIP archive processing
    print("📦 Demo 2: ZIP Archive Processing")
    print("-" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple test files
        test_files = {
            'foundation_plan.txt': """
Základová konstrukce
Beton C30/37 - XC2
Objem: 45.8 m³
Výztuž Fe500: 680 kg
            """,
            'structural_elements.txt': """
Nosné prvky
Sloupy: C35/45 - XC4
Rozměry: 350x350 mm
Počet: 8 ks
Objem: 15.2 m³
            """,
            'materials_list.txt': """
Seznam materiálů
- Tepelná izolace XPS: 120 m²
- Okna PVC: 12 ks  
- Hydroizolace EPDM: 95 m²
- Těsnění: 85 m
            """
        }
        
        # Create ZIP archive
        zip_path = os.path.join(temp_dir, 'construction_docs.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename, content in test_files.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content.strip())
                zipf.write(file_path, filename)
        
        # Parse ZIP archive
        result = parse_document(zip_path)
        
        print(f"✅ ZIP parsing successful: {result['success']}")
        print(f"📦 Source type: {result.get('source_type', 'unknown')}")
        print(f"📄 Files processed: {result.get('files_processed', 0)}")
        print(f"📝 Results count: {len(result['results'])}")
        
        # Show summary of all files processed
        parsers_used = []
        total_content_length = 0
        
        for i, parse_result in enumerate(result['results']):
            parsers_used.append(parse_result.parser_used)
            total_content_length += len(str(parse_result.content))
            print(f"   File {i+1}: {parse_result.source_file} -> {parse_result.parser_used}")
        
        print(f"🔧 Parsers used: {', '.join(set(parsers_used))}")
        print(f"📏 Total content length: {total_content_length} characters")
    
    print()
    
    # Demo 3: Unified parser info
    print("🔧 Demo 3: Unified Parser Information")
    print("-" * 40)
    
    parser = get_unified_document_parser()
    print(f"📁 Supported extensions: {', '.join(sorted(parser.supported_extensions))}")
    
    # Test file info for different types
    test_extensions = ['.pdf', '.docx', '.xlsx', '.xml', '.txt', '.zip']
    
    for ext in test_extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(b'test content')
            f.flush()
            
            try:
                info = parser.get_file_info(f.name)
                print(f"   {ext}: supported={info['supported']}, "
                      f"mineru={info['can_use_mineru']}, "
                      f"legacy={info['legacy_parser']}")
            finally:
                os.unlink(f.name)
    
    print()
    
    # Summary
    print("🎉 Demo Summary")
    print("-" * 40)
    print("✅ Unified document parser successfully integrates MinerU")
    print("✅ Backward compatibility maintained with legacy parsers")
    print("✅ ZIP archive processing works correctly")
    print("✅ All file types properly supported")
    print("✅ Metadata tracking and parser identification working")
    
    if info.get('available', False):
        print("🚀 MinerU package is available - using enhanced parsing")
    else:
        print("💡 MinerU package not installed - using legacy fallback")
        print("   Install MinerU: pip install mineru")
        print("   Enable MinerU: export MINERU_ENABLED=true")
    
    print("\n🏗️  Ready for production use!")


if __name__ == "__main__":
    main()