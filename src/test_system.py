#!/usr/bin/env python3
"""
Simple Test Script for Optimized BrowserControL01 System
=========================================================

Quick verification that all components work together.
Note: For full testing without browser deps, use test_core.py instead.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core import SystemConfig, StealthBrowserManager, HumanBehaviorEngine, AdaptiveDOMInteractor
from sites import site_registry
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


def test_site_system():
    """Test site-specific modules"""
    print("\n🎯 Testing site-specific system...")

    # Test registry
    supported_sites = site_registry.list_supported_sites()
    print(f"✅ Site registry: {supported_sites}")

    # Check expected sites are registered
    expected = ['google', 'amazon', 'ebay', 'wikipedia', 'chatgpt', 'generic']
    missing = [s for s in expected if s not in supported_sites]

    if missing:
        print(f"⚠️  Missing site modules: {missing}")
    else:
        print("✅ All expected site modules registered")


def test_system_integration():
    """Test full system integration"""
    print("\n🔗 Testing system integration...")

    from main import BrowserControlSystem

    system = BrowserControlSystem()
    capabilities = system.list_capabilities()

    print(f"✅ Supported sites: {capabilities['supported_sites']}")
    print(f"✅ Security available: {capabilities['security_available']}")
    print(f"✅ Features: {capabilities.get('features', [])}")


def test_config_system():
    """Test configuration system"""
    print("\n⚙️  Testing configuration system...")

    config = SystemConfig()

    # Test to_dict
    config_dict = config.to_dict()
    assert isinstance(config_dict, dict), "to_dict should return dict"
    print("✅ SystemConfig.to_dict() works")

    # Test site config
    google_config = config.get_site_config_object("google")
    assert google_config is not None, "Google config should exist"
    print(f"✅ Google config: {google_config.base_url}")

    # Test languages attribute
    assert hasattr(config, 'languages'), "Should have languages attribute"
    print(f"✅ Languages configured: {config.languages}")


def main():
    """Run all tests"""
    print("🚀 BrowserControL01 Optimized System Test")
    print("=" * 50)

    try:
        test_core_components()
        test_config_system()
        test_site_system()
        test_system_integration()

        print("\n✅ All tests passed! System is ready.")
        print("\n📋 Usage examples:")
        print("  python src/main.py info")
        print("  python src/main.py site google --operation search --params '{\"query\": \"AI\"}'")
        print("  python src/main.py wikipedia 'artificial intelligence'")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
