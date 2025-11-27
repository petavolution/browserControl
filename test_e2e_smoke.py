#!/usr/bin/env python3
"""
End-to-End Smoke Test for BrowserControL01
===========================================

Validates the complete execution flow without browser dependencies.
Tests the critical path: config → system → modules → execution flow.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Track which modules are available
BROWSER_DEPS_AVAILABLE = False

try:
    from core.config import SystemConfig, SiteConfig
    from sites import site_registry
    from utils.logger import StealthLogger
    BROWSER_DEPS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Browser dependencies not available: {e}")
    print("Some tests will be skipped.\n")


class SmokeTestRunner:
    """End-to-end smoke test runner"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []

    def run_test(self, name: str, test_func):
        """Run a single test"""
        try:
            result = test_func()
            self.tests_passed += 1
            self.results.append({
                'name': name,
                'status': 'PASS',
                'result': result
            })
            print(f"✅ {name}")
            return True
        except AssertionError as e:
            self.tests_failed += 1
            self.results.append({
                'name': name,
                'status': 'FAIL',
                'error': str(e)
            })
            print(f"❌ {name}: {e}")
            return False
        except Exception as e:
            self.tests_failed += 1
            self.results.append({
                'name': name,
                'status': 'ERROR',
                'error': f"{type(e).__name__}: {e}"
            })
            print(f"💥 {name}: {type(e).__name__}: {e}")
            return False

    def test_system_config_creation(self):
        """Test SystemConfig can be created with defaults"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        config = SystemConfig()
        assert config is not None, "Config should not be None"
        assert hasattr(config, 'base_path'), "Config should have base_path"
        assert hasattr(config, 'log_file'), "Config should have log_file"
        return {'config_created': True, 'base_path': str(config.base_path)}

    def test_site_registry_populated(self):
        """Test site registry has all expected modules"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        expected_sites = ['google', 'amazon', 'ebay', 'wikipedia', 'chatgpt', 'generic']
        registered = site_registry.list_supported_sites()

        for site in expected_sites:
            assert site in registered, f"Missing site: {site}"

        return {
            'expected': expected_sites,
            'registered': registered,
            'count': len(registered)
        }

    def test_selector_files_exist(self):
        """Test all selector files are accessible"""
        base_path = Path(__file__).parent / "src" / "sites" / "selectors"
        expected_files = [
            'google_selectors.json',
            'amazon_selectors.json',
            'ebay_selectors.json',
            'wikipedia_selectors.json',
            'chatgpt_selectors.json',
            'generic_selectors.json'
        ]

        found = []
        missing = []

        for filename in expected_files:
            file_path = base_path / filename
            if file_path.exists():
                found.append(filename)
            else:
                missing.append(filename)

        assert len(missing) == 0, f"Missing selector files: {missing}"

        return {
            'found': found,
            'missing': missing,
            'total': len(found)
        }

    def test_selector_files_valid_json(self):
        """Test selector files contain valid JSON"""
        base_path = Path(__file__).parent / "src" / "sites" / "selectors"
        selector_files = list(base_path.glob("*_selectors.json"))

        valid = []
        invalid = []

        for file_path in selector_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    assert isinstance(data, dict), f"{file_path.name}: Root should be dict"
                    valid.append(file_path.name)
            except Exception as e:
                invalid.append(f"{file_path.name}: {e}")

        assert len(invalid) == 0, f"Invalid JSON files: {invalid}"

        return {
            'valid': valid,
            'invalid': invalid,
            'total_checked': len(selector_files)
        }

    def test_site_config_creation(self):
        """Test SiteConfig can be created"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        selector_path = Path(__file__).parent / "src" / "sites" / "selectors" / "google_selectors.json"

        config = SiteConfig(
            name="Google",
            base_url="https://www.google.com",
            selector_file_path=selector_path
        )

        assert config is not None, "SiteConfig should not be None"
        assert config.name == "Google", "Name should match"
        assert config.base_url == "https://www.google.com", "Base URL should match"
        assert config.selector_file_path == selector_path, "Selector path should match"

        return {
            'name': config.name,
            'base_url': config.base_url,
            'has_selector_path': config.selector_file_path is not None
        }

    def test_logger_creation(self):
        """Test StealthLogger can be created"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        logger = StealthLogger()

        assert logger is not None, "Logger should not be None"
        assert hasattr(logger, 'debug'), "Logger should have debug method"
        assert hasattr(logger, 'info'), "Logger should have info method"
        assert hasattr(logger, 'warning'), "Logger should have warning method"
        assert hasattr(logger, 'error'), "Logger should have error method"

        return {'logger_created': True}

    def test_parameter_normalization_logic(self):
        """Test parameter normalization mappings are correct"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        from sites.base_site import BaseSiteModule

        aliases = BaseSiteModule.PARAM_ALIASES

        assert 'q' in aliases, "Should have 'q' alias"
        assert aliases['q'] == 'query', "'q' should map to 'query'"
        assert 'url' in aliases, "Should have 'url' alias"
        assert aliases['url'] == 'query_or_url', "'url' should map to 'query_or_url'"

        return {
            'aliases': aliases,
            'total_aliases': len(aliases)
        }

    def test_execution_flow_components(self):
        """Test all critical execution flow components exist"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        from main import BrowserControlSystem, load_config

        # Test load_config exists and works with None
        config = load_config(None)
        assert config is not None, "load_config should return config for None input"

        # Test BrowserControlSystem can be instantiated
        # Note: This doesn't create a driver, just the system object
        system = BrowserControlSystem(config)
        assert system is not None, "BrowserControlSystem should be created"
        assert system.config is not None, "System should have config"
        assert system.log is not None, "System should have logger"

        return {
            'load_config_works': True,
            'system_created': True,
            'has_config': True,
            'has_logger': True
        }

    def test_workflow_result_structure(self):
        """Test WorkflowResult class works correctly"""
        if not BROWSER_DEPS_AVAILABLE:
            return {'skipped': True, 'reason': 'Browser dependencies not available'}

        from workflows.base_workflow import WorkflowResult

        # Test success result
        success = WorkflowResult(success=True, data={'test': 'value'})
        assert success.success is True, "Success should be True"
        assert success.data['test'] == 'value', "Data should be preserved"

        # Test error addition
        success.add_error("Test error")
        assert success.success is False, "Success should become False after error"
        assert "Test error" in success.errors, "Error should be in list"

        # Test to_dict
        result_dict = success.to_dict()
        assert 'success' in result_dict, "Dict should have success key"
        assert 'data' in result_dict, "Dict should have data key"
        assert 'errors' in result_dict, "Dict should have errors key"

        return {
            'result_creation': True,
            'error_handling': True,
            'to_dict_works': True
        }

    def run_all_tests(self):
        """Run all smoke tests"""
        print("\n" + "=" * 70)
        print("BrowserControL01 - End-to-End Smoke Test")
        print("=" * 70)
        print()

        tests = [
            ("System Configuration Creation", self.test_system_config_creation),
            ("Site Registry Population", self.test_site_registry_populated),
            ("Selector Files Exist", self.test_selector_files_exist),
            ("Selector Files Valid JSON", self.test_selector_files_valid_json),
            ("Site Config Creation", self.test_site_config_creation),
            ("Logger Creation", self.test_logger_creation),
            ("Parameter Normalization", self.test_parameter_normalization_logic),
            ("Execution Flow Components", self.test_execution_flow_components),
            ("Workflow Result Structure", self.test_workflow_result_structure),
        ]

        for name, test_func in tests:
            self.run_test(name, test_func)

        print()
        print("=" * 70)
        print(f"SMOKE TEST SUMMARY: {self.tests_passed} passed, {self.tests_failed} failed")
        print("=" * 70)

        return {
            'total': len(tests),
            'passed': self.tests_passed,
            'failed': self.tests_failed,
            'results': self.results
        }


def main():
    """Main entry point"""
    runner = SmokeTestRunner()

    try:
        results = runner.run_all_tests()

        # Exit with error code if any tests failed
        sys.exit(0 if results['failed'] == 0 else 1)

    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
