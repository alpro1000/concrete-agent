#!/usr/bin/env python3
"""
Validation script to verify all fixes are working correctly
"""

import sys
import os

# Add project root to path
sys.path.append('/home/runner/work/concrete-agent/concrete-agent')

def test_prompt_loader():
    """Test PromptLoader fixes"""
    print("=" * 60)
    print("Testing PromptLoader Fixes")
    print("=" * 60)
    
    from app.core.prompt_loader import PromptLoader, get_prompt_loader
    
    # Test 1: get_prompt_config
    loader = PromptLoader()
    config = loader.get_prompt_config('tzd')
    assert 'model' in config, "Config should have 'model' key"
    assert config['model'] == 'claude-3-5-sonnet-20241022', "TZD should use Claude"
    print("✅ get_prompt_config('tzd') works correctly")
    
    # Test 2: Default config
    default_config = loader.get_prompt_config('unknown')
    assert 'model' in default_config, "Default config should have 'model' key"
    print("✅ get_prompt_config(unknown) returns default correctly")
    
    # Test 3: get_system_prompt
    prompt = loader.get_system_prompt('tzd')
    assert isinstance(prompt, str), "System prompt should be string"
    print("✅ get_system_prompt('tzd') works correctly")
    
    # Test 4: Singleton
    loader2 = get_prompt_loader()
    assert loader is not loader2, "Direct instantiation should create new instance"
    singleton1 = get_prompt_loader()
    singleton2 = get_prompt_loader()
    assert singleton1 is singleton2, "get_prompt_loader should return singleton"
    print("✅ Singleton pattern works correctly")
    
    print()
    return True


def test_router_files():
    """Test that router files exist and compile"""
    print("=" * 60)
    print("Testing Router Files")
    print("=" * 60)
    
    routers_dir = '/home/runner/work/concrete-agent/concrete-agent/app/routers'
    
    required_files = [
        'user_router.py',
        'results_router.py',
        'unified_router.py',
        'tzd_router.py',
        '__init__.py'
    ]
    
    for filename in required_files:
        filepath = os.path.join(routers_dir, filename)
        assert os.path.exists(filepath), f"{filename} should exist"
        
        # Try to compile
        with open(filepath, 'r') as f:
            code = f.read()
            compile(code, filepath, 'exec')
        
        print(f"✅ {filename} exists and compiles successfully")
    
    print()
    return True


def test_router_registration():
    """Test that routers are properly registered"""
    print("=" * 60)
    print("Testing Router Registration")
    print("=" * 60)
    
    # Read __init__.py
    init_file = '/home/runner/work/concrete-agent/concrete-agent/app/routers/__init__.py'
    with open(init_file, 'r') as f:
        content = f.read()
    
    required_routers = [
        'user_router',
        'results_router',
        'unified_router',
        'tzd_router'
    ]
    
    for router in required_routers:
        assert router in content, f"{router} should be in __init__.py"
        print(f"✅ {router} registered in __init__.py")
    
    print()
    return True


def test_agent_integration():
    """Test that agent can use get_prompt_config"""
    print("=" * 60)
    print("Testing Agent Integration")
    print("=" * 60)
    
    import inspect
    from app.agents.tzd_reader.agent import SecureAIAnalyzer
    
    # Check that analyze_with_llm_service uses get_prompt_config
    source = inspect.getsource(SecureAIAnalyzer.analyze_with_llm_service)
    assert 'get_prompt_config' in source, "Agent should use get_prompt_config"
    print("✅ SecureAIAnalyzer.analyze_with_llm_service uses get_prompt_config")
    
    # Check method exists
    loader_source = inspect.getsource(SecureAIAnalyzer.__init__)
    assert 'prompt_loader' in loader_source, "Agent should initialize prompt_loader"
    print("✅ SecureAIAnalyzer initializes prompt_loader")
    
    print()
    return True


def test_documentation():
    """Test that documentation files exist"""
    print("=" * 60)
    print("Testing Documentation")
    print("=" * 60)
    
    required_docs = [
        'FIXES_DOCUMENTATION.md',
        'FIXES_README.md',
        'FIXES_SUMMARY.json',
        'OUTPUT_SUMMARY.json'
    ]
    
    root_dir = '/home/runner/work/concrete-agent/concrete-agent'
    
    for doc in required_docs:
        filepath = os.path.join(root_dir, doc)
        assert os.path.exists(filepath), f"{doc} should exist"
        
        # Check file is not empty
        size = os.path.getsize(filepath)
        assert size > 0, f"{doc} should not be empty"
        
        print(f"✅ {doc} exists ({size} bytes)")
    
    print()
    return True


def main():
    """Run all validation tests"""
    print("\n" + "=" * 60)
    print("VALIDATION SCRIPT - Backend Fixes")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    try:
        test_prompt_loader()
    except Exception as e:
        print(f"❌ PromptLoader tests failed: {e}")
        all_passed = False
    
    try:
        test_router_files()
    except Exception as e:
        print(f"❌ Router file tests failed: {e}")
        all_passed = False
    
    try:
        test_router_registration()
    except Exception as e:
        print(f"❌ Router registration tests failed: {e}")
        all_passed = False
    
    try:
        test_agent_integration()
    except Exception as e:
        print(f"❌ Agent integration tests failed: {e}")
        all_passed = False
    
    try:
        test_documentation()
    except Exception as e:
        print(f"❌ Documentation tests failed: {e}")
        all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        print("\nStatus: Ready for Redeploy ✅")
        return 0
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
