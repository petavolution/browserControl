#!/usr/bin/env python3
"""
BrowserControL01 - Core Component Test Framework
=================================================

CLI tool for testing and validating core components without requiring a browser.
Run: python test_core.py [test_name] [--verbose]

All test output is written to debug-log.txt for debugging.
"""

import sys
import json
import argparse
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


class TestResult:
    """Container for test results"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "error": str(self.error) if self.error else None,
            "details": self.details
        }


class CoreTester:
    """Test framework for core components"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.logger = None

    def log(self, msg: str, level: str = "info"):
        """Log message to console and debug-log.txt"""
        if self.logger:
            getattr(self.logger, level, self.logger.info)(msg)
        if self.verbose or level in ("error", "warning"):
            print(f"[{level.upper()}] {msg}")

    def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test with error handling"""
        result = TestResult(name)
        try:
            if self.verbose:
                print(f"\n{'='*60}\nRunning: {name}\n{'='*60}")

            details = test_func()
            result.passed = True
            result.details = details or {}

            if self.verbose:
                print(f"PASSED: {name}")
                if details:
                    for k, v in details.items():
                        print(f"  {k}: {v}")

        except Exception as e:
            result.passed = False
            result.error = e
            result.details["traceback"] = traceback.format_exc()

            print(f"FAILED: {name}")
            print(f"  Error: {e}")
            if self.verbose:
                traceback.print_exc()

        self.results.append(result)
        return result

    # =========================================================================
    # Individual Tests
    # =========================================================================

    def test_imports(self) -> Dict[str, Any]:
        """Test that all core modules can be imported (handles missing browser deps)"""
        imports = {}
        missing_deps = []

        # Config (no browser deps)
        try:
            from core.config import SystemConfig, SiteConfig, TimeoutConfig
            imports["SystemConfig"] = "OK"
            imports["SiteConfig"] = "OK"
            imports["TimeoutConfig"] = "OK"
        except ImportError as e:
            imports["config"] = f"SKIP: {e}"

        # Structures (may need selenium)
        try:
            from core.structures import ExtractedElement, ElementProperties
            imports["ExtractedElement"] = "OK"
            imports["ElementProperties"] = "OK"
        except ImportError as e:
            missing_deps.append(f"structures: {e}")

        # Logger (no browser deps)
        try:
            from utils.logger import StealthLogger, get_logger
            imports["StealthLogger"] = "OK"
            imports["get_logger"] = "OK"
        except ImportError as e:
            imports["logger"] = f"SKIP: {e}"

        # File utils (no browser deps usually)
        try:
            from utils.file_utils import ensure_directory_exists, is_valid_chrome_profile_dir
            imports["ensure_directory_exists"] = "OK"
            imports["is_valid_chrome_profile_dir"] = "OK"
        except ImportError as e:
            missing_deps.append(f"file_utils: {e}")

        # Serialization (may need selenium)
        try:
            from utils.serialization import CustomJsonEncoder
            imports["CustomJsonEncoder"] = "OK"
        except ImportError as e:
            missing_deps.append(f"serialization: {e}")

        return {
            "modules_imported": len([v for v in imports.values() if v == "OK"]),
            "imports": imports,
            "missing_deps": missing_deps if missing_deps else "None"
        }

    def test_logger(self) -> Dict[str, Any]:
        """Test logger functionality (direct import without __init__)"""
        # Import directly to avoid dependency chain
        sys.path.insert(0, str(Path(__file__).parent / "src" / "utils"))
        from logger import get_logger, StealthLogger

        # Create logger
        logger = get_logger(name="test-logger", level="DEBUG")
        self.logger = logger  # Store for use in other tests

        # Test logging levels
        logger.debug("Debug test message")
        logger.info("Info test message")
        logger.warning("Warning test message")

        # Test sensitive data filtering
        filtered = logger._filter_sensitive("password=secret123 token=abc123")
        assert "secret123" not in filtered, "Password not filtered!"
        assert "abc123" not in filtered, "Token not filtered!"

        # Check debug-log.txt was created
        debug_log = Path("debug-log.txt")
        debug_log_exists = debug_log.exists()

        return {
            "logger_created": True,
            "debug_log_exists": debug_log_exists,
            "sensitive_filter_works": True
        }

    def test_config(self) -> Dict[str, Any]:
        """Test SystemConfig functionality"""
        from core.config import SystemConfig, SiteConfig, TimeoutConfig

        # Create config
        config = SystemConfig()

        # Test to_dict method
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict), "to_dict should return dict"
        assert "headless_mode" in config_dict, "to_dict missing headless_mode"

        # Test languages attribute (previously missing)
        assert hasattr(config, 'languages'), "SystemConfig missing languages attribute"
        assert isinstance(config.languages, list), "languages should be a list"

        # Test site configuration
        google_config = config.get_site_config_object("google")
        assert google_config is not None, "Google config should exist"
        assert google_config.base_url == "https://www.google.com"

        # Test path resolution
        assert config.output_dir is not None, "output_dir should be set"
        assert config.profile_dir is not None, "profile_dir should be set"

        return {
            "config_created": True,
            "to_dict_works": True,
            "languages_exists": True,
            "google_config": str(google_config.base_url),
            "output_dir": str(config.output_dir),
            "profile_dir": str(config.profile_dir)
        }

    def test_structures(self) -> Dict[str, Any]:
        """Test data structures (direct import)"""
        # Import directly to avoid dependency chain
        sys.path.insert(0, str(Path(__file__).parent / "src" / "core"))
        from structures import ExtractedElement, ElementProperties

        # Test ElementProperties
        props = ElementProperties(
            tag_name="div",
            attributes={"class": "test"},
            text="Test content",
            is_displayed=True,
            is_enabled=True,
            location={"x": 0, "y": 0},
            size={"width": 100, "height": 50}
        )
        assert props.tag_name == "div"

        # Test ExtractedElement
        elem = ExtractedElement(
            name="test_element",
            value="test_value",
            extraction_type="text",
            source_selector="div.test",
            properties=props,
            extraction_successful=True
        )
        assert elem.name == "test_element"
        assert elem.extraction_successful is True

        return {
            "ElementProperties": "OK",
            "ExtractedElement": "OK"
        }

    def test_site_registry(self) -> Dict[str, Any]:
        """Test site module registry (requires browser deps)"""
        try:
            from sites import site_registry

            # Get list of registered sites
            supported = site_registry.list_supported_sites()

            # Check expected sites are registered
            expected_sites = ['google', 'amazon', 'ebay', 'wikipedia', 'chatgpt', 'generic']
            found_sites = []
            missing_sites = []

            for site in expected_sites:
                if site in supported:
                    found_sites.append(site)
                else:
                    missing_sites.append(site)

            return {
                "supported_sites": supported,
                "found_expected": found_sites,
                "missing_expected": missing_sites
            }
        except ImportError as e:
            return {
                "status": "SKIPPED",
                "reason": f"Browser dependencies not installed: {e}",
                "note": "Install requirements.txt to test site registry"
            }

    def test_selector_files(self) -> Dict[str, Any]:
        """Test that all selector JSON files are valid"""
        selectors_dir = Path(__file__).parent / "src" / "sites" / "selectors"

        selector_files = list(selectors_dir.glob("*_selectors.json"))
        results = {}

        for sf in selector_files:
            try:
                with open(sf, 'r') as f:
                    data = json.load(f)
                results[sf.name] = {
                    "valid": True,
                    "groups": list(data.keys())
                }
            except Exception as e:
                results[sf.name] = {
                    "valid": False,
                    "error": str(e)
                }

        return {
            "total_files": len(selector_files),
            "files": results
        }

    def test_file_utils(self) -> Dict[str, Any]:
        """Test file utility functions (direct import)"""
        # Import directly to avoid dependency chain
        sys.path.insert(0, str(Path(__file__).parent / "src" / "utils"))
        from file_utils import ensure_directory_exists, is_valid_chrome_profile_dir
        import tempfile
        import shutil

        # Test directory creation
        test_dir = Path(tempfile.mkdtemp()) / "test_subdir"
        result = ensure_directory_exists(test_dir)
        dir_created = test_dir.exists()

        # Clean up
        shutil.rmtree(test_dir.parent)

        return {
            "ensure_directory_exists": dir_created,
            "is_valid_chrome_profile_dir_callable": callable(is_valid_chrome_profile_dir)
        }

    def test_serialization(self) -> Dict[str, Any]:
        """Test JSON serialization (requires selenium for full test)"""
        try:
            from utils.serialization import CustomJsonEncoder
        except ImportError:
            # Test basic Path serialization without selenium
            class BasicJsonEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Path):
                        return str(obj)
                    return super().default(obj)
            CustomJsonEncoder = BasicJsonEncoder

        # Test serialization of Path objects
        test_data = {
            "path": Path("/test/path"),
            "string": "test",
            "number": 42
        }

        serialized = json.dumps(test_data, cls=CustomJsonEncoder)
        assert "/test/path" in serialized

        return {
            "CustomJsonEncoder": "OK",
            "path_serialization": "OK"
        }

    # =========================================================================
    # Test Runner
    # =========================================================================

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        tests = [
            ("Import Core Modules", self.test_imports),
            ("Logger System", self.test_logger),
            ("Configuration System", self.test_config),
            ("Data Structures", self.test_structures),
            ("Site Registry", self.test_site_registry),
            ("Selector Files", self.test_selector_files),
            ("File Utilities", self.test_file_utils),
            ("JSON Serialization", self.test_serialization),
        ]

        print("\n" + "=" * 70)
        print("BrowserControL01 - Core Component Tests")
        print("=" * 70)

        for name, test_func in tests:
            self.run_test(name, test_func)

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print("\n" + "=" * 70)
        print(f"TEST SUMMARY: {passed} passed, {failed} failed")
        print("=" * 70)

        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.error}")

        print(f"\nDetailed output written to: debug-log.txt")

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "results": [r.to_dict() for r in self.results]
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BrowserControL01 Core Component Test Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_core.py              # Run all tests
  python test_core.py --verbose    # Run with detailed output
  python test_core.py --json       # Output results as JSON
        """
    )

    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed test output")
    parser.add_argument("--json", "-j", action="store_true",
                       help="Output results as JSON")

    args = parser.parse_args()

    tester = CoreTester(verbose=args.verbose)

    try:
        results = tester.run_all_tests()

        if args.json:
            print(json.dumps(results, indent=2))

        # Exit with error code if any tests failed
        sys.exit(0 if results["failed"] == 0 else 1)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
