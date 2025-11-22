#!/usr/bin/env python3
"""
BrowserControL01 - Working Entry Point
======================================

Functional entry point that handles import paths correctly.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Main entry point with working imports"""
    
    # Import after path setup
    from core.config import SystemConfig
    from core.stealth_browser import StealthBrowserManager
    from core.human_behavior import HumanBehaviorEngine
    from core.dom_interactor import AdaptiveDOMInteractor
    from utils.logger import get_logger
    from security.basic_stealth import BasicStealthManager
    
    parser = argparse.ArgumentParser(
        description="BrowserControL01 - Stealth Web Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s info                    # Show system capabilities
  %(prog)s test-google "AI news"   # Test Google search
  %(prog)s test-basic "https://example.com" "test input"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show system capabilities')
    
    # Test Google command
    google_parser = subparsers.add_parser('test-google', help='Test Google search')
    google_parser.add_argument('query', help='Search query')
    google_parser.add_argument('--max-results', type=int, default=5, help='Max results')
    
    # Test basic automation
    basic_parser = subparsers.add_parser('test-basic', help='Test basic automation')
    basic_parser.add_argument('url', help='Target URL')
    basic_parser.add_argument('input_text', help='Text to input')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize system
    config = SystemConfig()
    logger = get_logger()
    
    print("🚀 BrowserControL01 System")
    print("=" * 40)
    
    if args.command == 'info':
        print("📋 System Capabilities:")
        print("  ✅ Stealth browser automation")
        print("  ✅ Human behavior emulation")
        print("  ✅ Multi-strategy element finding")
        print("  ✅ Content extraction")
        print("  ✅ Basic security features")
        print("\n🔧 Available Components:")
        print("  - StealthBrowserManager")
        print("  - HumanBehaviorEngine") 
        print("  - AdaptiveDOMInteractor")
        print("  - BasicStealthManager")
        print("\n🎯 Test Commands:")
        print("  python run_system.py test-google 'artificial intelligence'")
        print("  python run_system.py test-basic 'https://example.com' 'test input'")
        
    elif args.command == 'test-google':
        print(f"🔍 Testing Google search for: {args.query}")
        print("⚠️  Note: Google module needs browser session - this is a framework test")
        
        # Test Google module structure
        try:
            from sites.google import GoogleSearchModule
            
            google_module = GoogleSearchModule(config=config, logger=logger)
            selectors = google_module.get_site_selectors()
            
            print("✅ Google module initialized")
            print(f"✅ Configured selectors: {len(selectors)} elements")
            print("✅ Ready for browser automation")
            
        except Exception as e:
            print(f"❌ Google module test failed: {e}")
            import traceback
            traceback.print_exc()
            
    elif args.command == 'test-basic':
        print(f"🌐 Testing basic automation")
        print(f"   URL: {args.url}")
        print(f"   Input: {args.input_text}")
        print("⚠️  Note: Full automation requires browser session")
        
        # Test component integration
        browser_mgr = StealthBrowserManager(config, logger)
        behavior = HumanBehaviorEngine(config, logger)
        dom = AdaptiveDOMInteractor(config, logger)
        security = BasicStealthManager(config, logger)
        
        print("✅ All components initialized")
        print("✅ Ready for automation workflow")
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 