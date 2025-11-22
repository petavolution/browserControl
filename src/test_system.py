#!/usr/bin/env python3
"""
Simple Test Script for Optimized BrowserControL01 System
=========================================================

Quick verification that all components work together.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core import SystemConfig, StealthBrowserManager, HumanBehaviorEngine, AdaptiveDOMInteractor
from workflows import TextIOWorkflow
from sites import site_registry, GoogleSearchModule
from utils.logger import get_logger


def test_core_components():
    """Test core component initialization"""
    print("🧪 Testing core components...")
    
    config = SystemConfig()
    logger = get_logger()
    
    # Test browser manager
    browser_manager = StealthBrowserManager(config, logger)
    print("✅ Browser manager initialized")
    
    # Test human behavior
    behavior = HumanBehaviorEngine(config, logger)
    print("✅ Human behavior engine initialized")
    
    # Test DOM interactor
    dom = AdaptiveDOMInteractor(config, logger)
    print("✅ DOM interactor initialized")


def test_workflow_system():
    """Test workflow framework"""
    print("\n🔄 Testing workflow system...")
    
    config = SystemConfig()
    logger = get_logger()
    
    workflow = TextIOWorkflow(config, logger)
    print("✅ Text I/O workflow initialized")
    
    # Test validation
    valid = workflow.validate_params(url="https://example.com", input_text="test")
    assert valid, "Validation should pass with required params"
    print("✅ Parameter validation works")


def test_site_system():
    """Test site-specific modules"""
    print("\n🎯 Testing site-specific system...")
    
    # Test registry
    supported_sites = site_registry.list_supported_sites()
    print(f"✅ Site registry: {supported_sites}")
    
    # Test Google module
    google_module = site_registry.get_module('google')
    if google_module:
        print("✅ Google module can be instantiated")
        selectors = google_module.get_site_selectors()
        assert 'search_input' in selectors, "Should have search input selector"
        print("✅ Google selectors configured")
    else:
        print("❌ Google module failed to instantiate")


def test_system_integration():
    """Test full system integration"""
    print("\n🔗 Testing system integration...")
    
    from main import BrowserControlSystem
    
    system = BrowserControlSystem()
    capabilities = system.list_capabilities()
    
    print(f"✅ System capabilities: {capabilities['workflows']}")
    print(f"✅ Supported sites: {capabilities['supported_sites']}")
    print(f"✅ Security enabled: {capabilities['security_enabled']}")


def main():
    """Run all tests"""
    print("🚀 BrowserControL01 Optimized System Test")
    print("=" * 50)
    
    try:
        test_core_components()
        test_workflow_system()
        test_site_system()
        test_system_integration()
        
        print("\n✅ All tests passed! System is ready.")
        print("\n📋 Usage examples:")
        print("  python src/main.py info")
        print("  python src/main.py site google search 'artificial intelligence'")
        print("  python src/main.py text 'https://example.com' --input-text 'test query'")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 