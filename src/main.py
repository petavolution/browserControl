#!/usr/bin/env python3
"""
BrowserControL01 - Simplified Main Entry Point
==============================================

Streamlined automation system focused on site-specific workflows.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import shutil # Import shutil for directory operations

# Core imports
from core import SystemConfig
from core.config import SiteConfig
from sites import site_registry, GoogleSearchModule, AmazonSearchModule, EbaySearchModule, ChatGPTModule, GenericSiteModule, WikipediaSiteModule
from utils.logger import get_logger
from utils.serialization import CustomJsonEncoder
from utils.file_utils import ensure_directory_exists, is_valid_chrome_profile_dir # Added new import

# Using undetected_chromedriver for anti-detection
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Security imports (optional)
try:
    from security.basic_stealth import BasicStealthManager
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


class BrowserControlSystem:
    """Main system orchestrator - simplified and focused"""
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or SystemConfig()
        self.log = get_logger(log_file=self.config.log_file)
        self.driver: Optional[uc.Chrome] = None # Initialize driver attribute
        
        # Initialize security if available
        self.security_manager = None
        if SECURITY_AVAILABLE and self.config.enable_basic_stealth:
            self.security_manager = BasicStealthManager(self.config, self.log)
        
        # Register site modules
        self._register_site_modules()
    
    def _register_site_modules(self) -> None:
        """Register all available site modules"""
        site_modules = [
            ('google', GoogleSearchModule),
            ('amazon', AmazonSearchModule),
            ('ebay', EbaySearchModule),
            ('chatgpt', ChatGPTModule),
            ('generic', GenericSiteModule),
            ('wikipedia', WikipediaSiteModule)
        ]
        
        for site_name, module_class in site_modules:
            try:
                site_registry.register(site_name, module_class)
                self.log.debug(f"Registered site module: {site_name}")
            except Exception as e:
                self.log.warning(f"Failed to register {site_name}: {e}")
    
    def _initialize_driver(self) -> uc.Chrome:
        """Initializes and returns a configured undetected_chromedriver instance."""
        self.log.info("Initializing undetected_chromedriver...")
        options = ChromeOptions()

        # Profile Path Setup for undetected-chromedriver
        # uc.Chrome uses user_data_dir directly.
        profile_name_to_use = getattr(self.config, 'current_profile_name', 'default')
        user_data_dir_for_uc = None # Will be set if profile is used

        if profile_name_to_use:
            # uc.Chrome expects user_data_dir to be the *parent* of the profile folder if you want to switch profiles using options.
            # However, it's often simpler to let uc manage its own profile structure within a given user_data_dir, 
            # or point it to a specific Chrome profile directory.
            # For consistency with how Chrome handles profiles, we specify the main user data directory
            # and then the profile directory name.
            # Let's assume self.config.profile_dir is the root for all profiles (e.g., ~/.config/chromium or similar)
            # And profile_name_to_use is the actual profile folder name (e.g., "Default", "Profile 1")
            
            # uc.Chrome can take a user_data_dir. If you provide this, it will use/create a profile within it.
            # To use a *specific existing* Chrome profile, you point user_data_dir to the *actual profile folder*.
            # Example: user_data_dir='/home/user/.config/google-chrome/Profile 1'
            
            profile_path = self.config.profile_dir / profile_name_to_use
            ensure_directory_exists(profile_path) # Ensure the specific profile directory itself exists
            user_data_dir_for_uc = str(profile_path)
            options.add_argument(f"--profile-directory={profile_name_to_use}") # This might be redundant if user_data_dir points directly to profile_path
            self.log.info(f"Attempting to use browser profile for undetected_chromedriver: {str(profile_path)}")
        else:
            self.log.info("No specific profile name provided for undetected_chromedriver, using its default session.")

        # Headless mode for undetected-chromedriver
        headless_for_uc = self.config.headless_mode
        if headless_for_uc:
            self.log.info("Headless mode configured for undetected_chromedriver.")
        else:
            options.add_argument("--window-size=1920,1080")

        # User-Agent Override
        if self.config.user_agent_override:
            options.add_argument(f"user-agent={self.config.user_agent_override}")
            self.log.info(f"User-Agent override applied: {self.config.user_agent_override}")

        # Add additional Chrome options from BasicStealthManager
        if self.security_manager and hasattr(self.security_manager, 'get_additional_chrome_options'):
            additional_opts = self.security_manager.get_additional_chrome_options()
            if additional_opts:
                self.log.info(f"Applying additional Chrome options from BasicStealthManager: {additional_opts}")
                for opt in additional_opts:
                    options.add_argument(opt)

        try:
            driver = uc.Chrome(
                options=options,
                headless=headless_for_uc,
                user_data_dir=user_data_dir_for_uc
            )
            self.log.info("undetected_chromedriver initialized successfully.")

            # Apply JS-based stealth measures AFTER driver is initialized
            if self.security_manager and hasattr(self.security_manager, 'apply_js_stealth_to_driver'):
                self.log.info("Applying JS-based stealth measures from BasicStealthManager...")
                self.security_manager.apply_js_stealth_to_driver(driver)

            return driver
        except Exception as e:
            self.log.error(f"Failed to initialize undetected_chromedriver: {e}", exc_info=True)
            raise

    def get_driver(self, profile_name_override: Optional[str] = None) -> uc.Chrome:
        """Returns an initialized WebDriver instance. Initializes if not already done."""
        # Profile handling needs to be more robust. If profile_name_override is given,
        # and driver is already running with a different profile, it should ideally close
        # the old one and start a new one. For now, it just initializes if no driver exists.
        if not self.driver or not self.is_driver_active(): # is_driver_active is a hypothetical method
            # Potentially pass profile_name_override to _initialize_driver if it sets it on options
            # self.driver = self._initialize_driver() 
            # Store the profile name used to initialize this driver instance
            # This is a simplified way to handle it. A more robust solution might involve
            # checking if the requested profile_name_override matches self._current_driver_profile_name
            # and re-initializing if it doesn't.
            
            # Set current_profile_name on config before initializing if override is present
            original_profile_name = getattr(self.config, 'current_profile_name', None)
            if profile_name_override:
                setattr(self.config, 'current_profile_name', profile_name_override)
            
            self.driver = self._initialize_driver()

            # Restore original profile name on config if it was temporarily changed
            if profile_name_override and original_profile_name is not None:
                setattr(self.config, 'current_profile_name', original_profile_name)
            elif profile_name_override and original_profile_name is None: # Was not set before
                if hasattr(self.config, 'current_profile_name'): # Python 3.9+ use delattr, for now just set to None or remove if safe
                    try:
                        delattr(self.config, 'current_profile_name')
                    except AttributeError:
                        pass # was not there anyway

        return self.driver

    def is_driver_active(self) -> bool:
        """Checks if the WebDriver session is still active."""
        if not self.driver:
            return False
        try:
            _ = self.driver.current_url 
            # For undetected-chromedriver, sometimes checking window_handles is more robust if current_url fails on a closed browser
            # if not self.driver.window_handles:
            # return False            
            return True
        except Exception:
            return False

    def close_driver(self):
        """Closes the WebDriver session if it's active."""
        if self.driver and self.is_driver_active():
            self.log.info("Closing WebDriver...")
            try:
                self.driver.quit()
            except Exception as e:
                self.log.error(f"Error quitting WebDriver: {e}", exc_info=True)
            finally:
                self.driver = None
        else:
            self.log.debug("WebDriver not active or already closed.")

    def execute_site_workflow(self, site_name: str, operation: str, **params) -> Dict[str, Any]:
        """Execute site-specific workflow using the managed WebDriver."""
        self.log.info(f"Executing {operation} on {site_name} with params: {params}")
        
        profile_name = params.pop('profile', None) or getattr(self.config, 'current_profile_name', 'default')
        driver = self.get_driver(profile_name_override=profile_name)

        # Create SiteConfig for the specific module (except for "generic" which handles its own if not provided)
        current_site_config: Optional[SiteConfig] = None
        if site_name != "generic":
            # Attempt to get site-specific parameters from SystemConfig
            # This part assumes SystemConfig has a way to provide these details.
            # For example, self.config.sites.get(site_name) might return a dict of params.
            site_params = self.config.get_site_configuration_details(site_name) # Hypothetical method
            
            if not site_params:
                error_msg = f"Configuration details for site '{site_name}' not found in SystemConfig."
                self.log.error(error_msg)
                return {'success': False, 'error': error_msg}

            # Construct selector file path (convention-based if not absolute)
            # Default convention: src/sites/selectors/{site_name}_selectors.json
            # Base path for selectors can be derived from config or a fixed relative path.
            # Using a robust way to get to src/sites/selectors from config.base_path
            selectors_dir = self.config.base_path / "src" / "sites" / "selectors"
            # Use selector_file_name_part from site_params if available, otherwise default to site_name
            sfn_part = site_params.get('selector_file_name_part', site_name.lower())
            default_selector_filename = f"{sfn_part}_selectors.json"
            selector_file = selectors_dir / default_selector_filename
            
            # site_params might override selector_file_path or parts of it
            selector_file_path_from_config = site_params.get('selector_file_path')
            if selector_file_path_from_config:
                # If it's a relative path, resolve it against config.base_path or another anchor
                # If absolute, use as is.
                # For now, assume it can be a direct Path or string that Path can take.
                selector_file = Path(selector_file_path_from_config) 
                if not selector_file.is_absolute():
                     # Define how relative paths in config are resolved, e.g. w.r.t. config.base_path
                     selector_file = self.config.base_path / selector_file_path_from_config
            
            current_site_config = SiteConfig(
                name=site_params.get('name', site_name.capitalize()),
                base_url=site_params.get('base_url', ""),
                selector_file_path=selector_file if selector_file.exists() else None, # Pass Path object
                custom_params=site_params.get('custom_params', {})
            )
            self.log.info(f"Constructed SiteConfig for '{site_name}': URL='{current_site_config.base_url}', Selectors='{current_site_config.selector_file_path}'")
        else:
            self.log.debug("For 'generic' site, SiteConfig will be handled by the module itself if not explicitly passed.")
            # Optionally, one could still construct and pass a default SiteConfig for generic here if desired.

        site_module_instance = site_registry.get_module(
            site_name,  # Pass site_name directly as the first argument
            config=self.config,  # SystemConfig
            logger=self.log,
            driver=driver,
            site_config=current_site_config # Pass the (optional) SiteConfig instance
        )
        
        if not site_module_instance:
            return {
                'success': False,
                'error': f"Unsupported site: {site_name}",
                'available_sites': site_registry.list_supported_sites()
            }
        
        # Execute workflow
        try:
            params['operation'] = operation
            return site_module_instance.start_execution(**params)
        except Exception as e:
            self.log.error(f"Site workflow failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_external_session(self, source_profile_path_str: str, target_bot_profile_name: str, overwrite: bool = False) -> Dict[str, Any]:
        """Imports a Chrome session from an external profile path to a bot profile."""
        self.log.info(f"Attempting to import session from '{source_profile_path_str}' to bot profile '{target_bot_profile_name}'.")

        print("="*70)
        print("⚠️ IMPORTANT INSTRUCTION FOR SESSION IMPORT ⚠️")
        print("Please COMPLETELY CLOSE ALL instances of your regular Chrome browser that might be using the source profile path:")
        print(f"  {source_profile_path_str}")
        print("This is crucial to ensure all profile files are unlocked and can be copied correctly.")
        print("Failure to close Chrome may result in a corrupted or incomplete session import.")
        print("="*70)
        input("Press Enter in this console AFTER you have completely closed your regular Chrome browser... ")
        self.log.info("User acknowledged Chrome closure prompt. Proceeding with session import.")

        source_profile_path = Path(source_profile_path_str)
        if not source_profile_path.exists():
            return {'success': False, 'error': f"Source profile path does not exist: {source_profile_path}"}
        
        if not is_valid_chrome_profile_dir(source_profile_path, self.log):
            # is_valid_chrome_profile_dir will log details
            return {'success': False, 'error': f"Source path {source_profile_path} does not appear to be a valid Chrome profile directory."}

        target_bot_profile_dir = self.config.profile_dir / target_bot_profile_name

        if target_bot_profile_dir.exists():
            if not overwrite:
                return {'success': False, 'error': f"Target bot profile '{target_bot_profile_name}' already exists at {target_bot_profile_dir}. Use --overwrite to replace."}
            else:
                try:
                    self.log.warning(f"Overwriting existing target bot profile: {target_bot_profile_dir}")
                    shutil.rmtree(target_bot_profile_dir)
                except Exception as e_rm:
                    return {'success': False, 'error': f"Failed to remove existing target profile {target_bot_profile_dir}: {e_rm}"}
        
        try:
            self.log.info(f"Copying profile from {source_profile_path} to {target_bot_profile_dir}...")
            shutil.copytree(source_profile_path, target_bot_profile_dir, dirs_exist_ok=True)
            self.log.info(f"Successfully imported session to bot profile: {target_bot_profile_name}")
            return {
                'success': True, 
                'message': f"Session successfully imported from {source_profile_path} to bot profile '{target_bot_profile_name}' at {target_bot_profile_dir}.",
                'bot_profile_name': target_bot_profile_name,
                'bot_profile_path': str(target_bot_profile_dir)
            }
        except Exception as e_cp:
            self.log.error(f"Failed to copy profile: {e_cp}", exc_info=True)
            return {'success': False, 'error': f"Failed to copy profile from {source_profile_path} to {target_bot_profile_dir}: {e_cp}"}
    
    def list_capabilities(self) -> Dict[str, Any]:
        """List system capabilities"""
        return {
            "supported_sites": site_registry.list_supported_sites(),
            "config": self.config.to_dict() if hasattr(self.config, 'to_dict') else vars(self.config),
            "security_available": SECURITY_AVAILABLE,
            "basic_stealth_enabled": self.security_manager is not None,
            "features": [
                "Stealth browser automation",
                "Human behavior emulation",
                "Multi-strategy element finding",
                "Content extraction",
                "Session persistence"
            ]
        }


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BrowserControL01 - Stealthy Web Automation System")
    parser.add_argument("--config", type=Path, help="Path to a custom JSON SystemConfig file.")
    parser.add_argument("--profile", type=str, help="Browser profile name to use for this session.")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Generic 'site' command parser
    site_parser = subparsers.add_parser("site", help="Interact with a specific site module.")
    site_parser.add_argument("site_name", help="Name of the site module to use (e.g., google, amazon, generic).")
    site_parser.add_argument("query", nargs='?', help="Search query or input text (optional, can also use --query or --params).")
    site_parser.add_argument("--operation", default="search", help="Operation to perform (e.g., search, get_data, interact). Default: search.")
    site_parser.add_argument("--query", "-q", dest="query_flag", help="Search query (alternative to positional argument).")
    site_parser.add_argument("--url", type=str, help="URL for operations that require it (e.g., generic interact).")
    site_parser.add_argument("--extraction-config", type=json.loads, help="JSON string for extraction configuration (e.g., '{\"type\": \"article\"').")
    site_parser.add_argument("--params", type=json.loads, help="JSON string of additional parameters for the operation.")
    site_parser.add_argument("--profile", help="Specific browser profile to use for this operation.")

    # Wikipedia-specific command parser
    wiki_parser = subparsers.add_parser("wikipedia", help="Interact with Wikipedia (search, get text, download images)")
    wiki_parser.add_argument("query_or_url", help="Wikipedia search query or direct URL.")
    wiki_parser.add_argument("--no-text", action="store_true", help="Disable text extraction.")
    wiki_parser.add_argument("--image-min-width", type=int, default=640, help="Minimum width for images to download (set to 0 to disable image download). Default: 640px.")
    wiki_parser.add_argument("--output-folder-name", type=str, help="Specific name for the output subfolder for this run (optional).")
    wiki_parser.add_argument("--depth", type=int, default=0, help="Exploration depth for following links. Default: 0 (no exploration).")
    wiki_parser.add_argument("--max-pages", type=int, default=1, help="Maximum number of pages to fetch during exploration (including initial). Default: 1.")
    wiki_parser.add_argument("--follow-keywords", nargs='+', help="List of keywords to look for in link text to guide exploration (e.g., genetics evolution).")

    # Admin/Utility commands
    admin_parser = subparsers.add_parser("admin", help="Administrative and utility tasks")

    return parser


def load_config(config_file: Path = None) -> SystemConfig:
    """Load configuration from file"""
    config = SystemConfig()
    
    if config_file and config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Apply configuration
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    return config


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load configuration
    config_file = Path(args.config) if hasattr(args, 'config') and args.config else None
    config = load_config(config_file)
    
    # Adjust logging level
    if hasattr(args, 'verbose') and args.verbose:
        config.log_file = None  # Console only for verbose mode
    
    # Enable manual intervention if flag is set
    if hasattr(args, 'manual_intervention') and args.manual_intervention:
        config.enable_manual_intervention_prompts = True
        print("❗ Manual intervention prompts ENABLED for this session.")

    # Initialize system
    system = BrowserControlSystem(config)
    
    result = None # Initialize result
    try:
        if args.command == 'info':
            # Show system info
            capabilities = system.list_capabilities()
            print("🤖 BrowserControL01 System Information")
            print("=" * 40)
            print(f"Supported Sites: {', '.join(capabilities['supported_sites'])}")
            print(f"Security Enabled: {capabilities['security_available']}")
            print("\nFeatures:")
            for feature in capabilities['features']:
                print(f"  • {feature}")
            
        elif args.command == 'generic':
            # Execute generic site interaction
            print(f"🚀 Executing generic interaction for: {args.url}")
            
            extraction_config = {
                "type": args.extraction_type,
                "custom_selectors": args.extraction_custom_selectors or [],
                "elements_to_extract": []
            }
            if args.extraction_elements_json:
                try:
                    json_input = args.extraction_elements_json
                    if Path(json_input).is_file():
                        with open(json_input, 'r') as f_json:
                            extraction_config["elements_to_extract"] = json.load(f_json)
                    else:
                        extraction_config["elements_to_extract"] = json.loads(json_input)
                except Exception as e_json:
                    print(f"⚠️ Could not parse --extraction-elements-json: {e_json}. It will be ignored.")

            site_params = {
                'url': args.url,
                'input_text': args.input_text,
                'input_selectors': args.input_selectors,
                'click_selectors': args.click_selectors,
                'extraction_config': extraction_config,
                'profile': args.profile
            }

            # Use execute_site_workflow with site='generic' and operation='interact'
            result = system.execute_site_workflow(
                site_name='generic',
                operation='interact', 
                **site_params
            )

            # Save results to file (specific for generic command)
            output_file = Path(args.output_file)
            try:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4, cls=CustomJsonEncoder)
                print(f"✅ Generic interaction results saved to: {output_file.resolve()}")
            except Exception as e:
                print(f"❌ Error saving generic interaction results: {e}")

        elif args.command == 'site':
            # Ensure params is a dict, even if not provided
            operation_params = args.params if args.params is not None else {}

            # Build params from flags (explicit flags take priority)
            temp_params_from_flags = {}

            # Handle query: positional arg > --query flag > --params
            query_value = args.query or getattr(args, 'query_flag', None)
            if query_value:
                temp_params_from_flags['query'] = query_value

            if args.url:
                temp_params_from_flags['url'] = args.url
            if args.extraction_config:
                temp_params_from_flags['extraction_config'] = args.extraction_config
            if args.profile:
                temp_params_from_flags['profile'] = args.profile

            # Merge: explicit flags first, then --params JSON data (which can override)
            final_operation_params = {**temp_params_from_flags, **operation_params}

            results = system.execute_site_workflow(args.site_name, args.operation, **final_operation_params)
            # Output for site command
            print(json.dumps(results, indent=4, cls=CustomJsonEncoder))
            # Optional: Save to file based on args if 'site' command has output args
        
        elif args.command == 'import-session':
            # Execute import session workflow
            if not args.source_profile_path or not args.target_bot_profile_name:
                print("❌ Missing required arguments for import-session command")
                sys.exit(1)
            
            result = system.import_external_session(args.source_profile_path, args.target_bot_profile_name, args.overwrite)

        elif args.command == "wikipedia":
            system.log.info(f"Wikipedia command initiated with query: {args.query_or_url}")
            result = system.execute_site_workflow(
                site_name='wikipedia',
                operation='get_data', 
                query_or_url=args.query_or_url,
                extract_text=not args.no_text,
                download_images_wider_than=args.image_min_width,
                output_subfolder_name=args.output_folder_name,
                exploration_depth=args.depth,
                max_pages_to_explore=args.max_pages,
                keywords_to_follow=args.follow_keywords
            )
            print(json.dumps(result, indent=4, cls=CustomJsonEncoder))
            if result and result.get("success"):
                 data = result.get('data', {})
                 output_path = data.get('output_path', 'N/A')
                 system.log.info(f"✅ Wikipedia workflow completed. Output path: {output_path}")
            else:
                 error_msg = result.get('error', 'Unknown error') if result else 'Workflow returned None'
                 system.log.error(f"❌ Wikipedia workflow failed. Error: {error_msg}")

    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        system.log.error(f"System critical failure: {e}", exc_info=True)
        print(f"SYSTEM CRITICAL FAILURE: {e}")
    finally:
        if hasattr(system, 'security_manager') and system.security_manager and hasattr(system.security_manager, 'cleanup'):
            system.security_manager.cleanup()
        # Close the main system driver if it was initialized
        if system: # Ensure system was initialized
            system.close_driver()
        # Add any other global cleanup here
        print("\n🤖 BrowserControL01 session ended.")


if __name__ == "__main__":
    main() 