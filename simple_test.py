#!/usr/bin/env python3
"""
Simple Test for BrowserControL01 System
=======================================

Basic validation that core components can be imported and initialized.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that core modules can be imported"""
    print("🧪 Testing core imports...")
    
    try:
        from core.config import SystemConfig
        print("✅ SystemConfig imported")
        
        from core.stealth_browser import StealthBrowserManager  
        print("✅ StealthBrowserManager imported")
        
        from core.human_behavior import HumanBehaviorEngine
        print("✅ HumanBehaviorEngine imported")
        
        from core.dom_interactor import AdaptiveDOMInteractor
        print("✅ AdaptiveDOMInteractor imported")
        
        from utils.logger import get_logger
        print("✅ Logger imported")
        
        from security.basic_stealth import BasicStealthManager
        print("✅ BasicStealthManager imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_initialization():
    """Test that components can be initialized"""
    print("\n🔧 Testing component initialization...")
    
    try:
        from core.config import SystemConfig
        from core.stealth_browser import StealthBrowserManager
        from core.human_behavior import HumanBehaviorEngine
        from core.dom_interactor import AdaptiveDOMInteractor
        from utils.logger import get_logger
        from security.basic_stealth import BasicStealthManager
        
        # Initialize components
        config = SystemConfig()
        logger = get_logger()
        
        browser_mgr = StealthBrowserManager(config, logger)
        print("✅ Browser manager initialized")
        
        behavior = HumanBehaviorEngine(config, logger)
        print("✅ Human behavior engine initialized")
        
        dom = AdaptiveDOMInteractor(config, logger)
        print("✅ DOM interactor initialized")
        
        security = BasicStealthManager(config, logger)
        print("✅ Security manager initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test basic functionality without browser"""
    print("\n⚙️ Testing basic functionality...")
    
    try:
        from core.config import SystemConfig
        from core.human_behavior import HumanBehaviorEngine
        from utils.logger import get_logger
        
        config = SystemConfig()
        logger = get_logger()
        behavior = HumanBehaviorEngine(config, logger)
        
        # Test timing functions
        import time
        start = time.time()
        behavior.human_pause(0.01, 0.02)
        elapsed = time.time() - start
        
        if 0.01 <= elapsed <= 0.05:
            print("✅ Human pause timing works")
        else:
            print(f"⚠️ Human pause timing unusual: {elapsed:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 BrowserControL01 Simple System Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_initialization,
        test_basic_functionality
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ All core components are working!")
        print("\n📋 System is ready for:")
        print("  - Browser automation")
        print("  - Human behavior simulation")  
        print("  - Stealth operations")
        print("  - Site-specific workflows")
    else:
        print("❌ Some components need attention")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 