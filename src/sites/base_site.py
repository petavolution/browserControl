#!/usr/bin/env python3
"""
Base Site Module for BrowserControL01
=====================================

Abstract base class for site-specific automation modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import json
import pathlib
import time

from workflows.base_workflow import BaseWorkflow
from core.config import SiteConfig, WorkflowConfig, SystemConfig
from core.structures import ExtractedElement
from core.human_behavior import HumanBehaviorEngine
from core.dom_interactor import AdaptiveDOMInteractor
import undetected_chromedriver as uc
from utils.logger import StealthLogger


class BaseSiteModule(BaseWorkflow):
    """Abstract base class for site-specific automation"""

    # Parameter name mapping for different operations
    PARAM_ALIASES = {
        'q': 'query',           # Short form for query
        'url': 'query_or_url',  # URL can be used as query
        'search': 'query',      # Search term alias
        'term': 'query',        # Term alias
    }

    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: StealthLogger, site_config: SiteConfig, **kwargs):
        super().__init__(config=config, logger=logger, **kwargs)
        self.driver = driver
        self.site_config = site_config
        self._site_selectors_data: Dict[str, Dict[str, str]] = self._load_site_selectors()
        self.log.info(f"BaseSiteModule for {self.site_config.name} initialized with a managed WebDriver.")
        self.behavior = HumanBehaviorEngine(config=config, logger=logger) if driver else None
        self.dom = AdaptiveDOMInteractor(config=config, logger=logger) # DOM interactor doesn't always need driver at init
        
    def _load_site_selectors(self, selector_file: Optional[pathlib.Path] = None) -> Dict[str, Dict[str, str]]:
        """Loads site-specific selectors from a JSON file."""
        if selector_file is None:
            if self.site_config.selector_file_path:
                selector_file = self.site_config.selector_file_path
            else:
                # Default convention: src/sites/selectors/{site_name}_selectors.json
                site_name_lower = self.site_config.name.lower()
                # Assuming this file is in src/sites/ and selectors are in src/sites/selectors/
                current_file_dir = pathlib.Path(__file__).parent
                selector_file = current_file_dir / "selectors" / f"{site_name_lower}_selectors.json"

        if not selector_file.exists():
            self.log.warning(f"Selector file not found: {selector_file}. No site-specific selectors loaded for {self.site_config.name}.")
            return {}
        
        try:
            with open(selector_file, 'r') as f:
                selectors = json.load(f)
                self.log.info(f"Successfully loaded selectors for {self.site_config.name} from {selector_file}")
                return selectors
        except Exception as e:
            self.log.error(f"Error loading selector file {selector_file}: {e}")
            return {}
    
    @abstractmethod
    def search(self, query: str, **params) -> Dict[str, Any]:
        """Perform site-specific search"""
        pass
    
    def get_site_selectors(self, group_key: str) -> Dict[str, str]:
        """Get a group of site-specific selectors (e.g., for 'search_page')."""
        group = self._site_selectors_data.get(group_key, {})
        if not group:
            self.log.warning(f"Selector group '{group_key}' not found for site {self.site_config.name}.")
        return group
    
    def get_selector(self, group_key: str, element_key: str) -> Optional[Union[str, List[str]]]:
        """Get a single site-specific selector string or a list of selector strings."""
        selectors_group = self.get_site_selectors(group_key)
        selector = selectors_group.get(element_key)
        if selector is None:
            self.log.warning(f"Selector for '{element_key}' in group '{group_key}' not found for site {self.site_config.name}.")
        return selector
    
    def validate_params(self, **params) -> bool:
        """Base validation for site modules"""
        if 'query' not in params or not params['query']:
            self.log.error("Query parameter is required")
            return False
        return True
    
    def execute(self, **params) -> Dict[str, Any]:
        """Execute site-specific workflow by dynamically calling the operation method."""
        operation = params.pop('operation', 'search') # Pop operation, keep other params
        
        if hasattr(self, operation) and callable(getattr(self, operation)):
            operation_method = getattr(self, operation)
            # Prepare arguments for the operation method.
            # It expects specific named args (like query for search, query_or_url for get_data)
            # and then **params for any extras.
            # We need to inspect the method signature or make assumptions.
            # For now, let's assume the primary query-like arg is handled by the method,
            # and it can take **params for the rest.
            self.log.info(f"Executing operation '{operation}' on {self.site_config.name} with params: {params}")
            try:
                return operation_method(**params) # Pass remaining params
            except Exception as e:
                self.log.error(f"Error during operation '{operation}' on {self.site_config.name}: {e}", exc_info=True)
                current_url = None
                if self.driver and self.is_driver_active_from_module(): # Ensure driver check is safe
                    try:
                        current_url = self.driver.current_url
                    except Exception: pass # Driver might be dead
                return self._create_error_result(f"Operation '{operation}' failed: {str(e)}", current_url=current_url)
        else:
            self.log.error(f"Unsupported operation: {operation} for site {self.site_config.name}")
            return self._create_error_result(f"Unsupported operation: {operation}")
    
    def _create_success_result(self, data: Dict[str, Any], message: Optional[str] = None) -> Dict[str, Any]:
        """Creates a standardized success result dictionary."""
        return {
            'success': True,
            'message': message or f"{self.site_config.name} operation successful.",
            'data': data
        }

    def _create_error_result(self, error_message: str, current_url: Optional[str] = None, error_code: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates a standardized error result dictionary."""
        # Log the error automatically when this method is called
        log_msg = f"{self.site_config.name} Error: {error_message}"
        if current_url: log_msg += f" (URL: {current_url})"
        if error_code: log_msg += f" (Code: {error_code})"
        self.log.error(log_msg)
        
        return {
            'success': False,
            'error': error_message,
            'current_url': current_url,
            'error_code': error_code,
            'data': data # Allow passing some data even in errors (e.g. partial results)
        }

    def navigate_to_site(self, driver, path: str = "") -> bool:
        """Navigate to the site's base URL"""
        url = self.site_config.base_url + path
        if hasattr(self, 'navigate_with_retry'):
            return self.navigate_with_retry(driver, url)
        elif hasattr(self.browser_manager, 'navigate_to'):
            return self.browser_manager.navigate_to(url)
        else:
            self.log.error("Navigation method not found in BaseSiteModule or its components.")
            return False
    
    def find_site_element(self, driver, group_key: str, element_key: str, 
                            search_context=None, 
                            retries: Optional[int] = None, 
                            pause_sec: Optional[float] = None,
                            log_not_found: bool = True,
                            shadow_path: Optional[List[str]] = None) -> Optional[ExtractedElement]:
        """Find an element using site-specific selectors with retries and shadow DOM support.

        Args:
            driver: The WebDriver instance (used if search_context is None).
            group_key: The key for the selector group in the JSON file.
            element_key: The key for the specific selector within the group.
            search_context: The context to search within (e.g., WebDriver, WebElement, ShadowRoot).
                            Defaults to driver if None.
            retries (Optional[int]): Number of retries. Defaults to site/system config.
            pause_sec (Optional[float]): Pause duration between retries. Defaults to site/system config.
            log_not_found (bool): Whether to log if the element is not found.
            shadow_path (Optional[List[str]]): Path of CSS selectors for shadow DOM hosts.

        Returns:
            Optional[ExtractedElement]: The found element, or None.
        """
        selector_or_list = self.get_selector(group_key, element_key)
        if not selector_or_list:
            if log_not_found:
                self.log.warning(f"No selector found for {group_key}.{element_key} in {self.site_config.name}.")
            return None
        
        selectors_to_try: List[Union[str, Dict[str, str]]] = []
        if isinstance(selector_or_list, list):
            selectors_to_try.extend(selector_or_list)
        elif isinstance(selector_or_list, (str, dict)):
            selectors_to_try.append(selector_or_list)
        else:
            if log_not_found:
                self.log.warning(f"Invalid selector format for {group_key}.{element_key}: {selector_or_list}")
            return None

        context_to_search = search_context if search_context else driver
        logical_name_base = f"{self.site_config.name}_{group_key}_{element_key}"

        # Determine retry and pause values: Site JSON -> SystemConfig
        effective_retries = retries
        if effective_retries is None:
            effective_retries = self.site_config.custom_params.get(
                'retry_attempts_for_elements', self.config.default_retry_attempts
            )
        
        effective_pause_sec = pause_sec
        if effective_pause_sec is None:
            effective_pause_sec = self.site_config.custom_params.get(
                'retry_pause_sec_for_elements', self.config.default_retry_pause_sec
            )

        for i, selector_item in enumerate(selectors_to_try):
            search_params_for_dom = {}
            current_logical_name = f"{logical_name_base}_attempt{i}"
            processed_selector_str = "N/A"

            if isinstance(selector_item, str):
                processed_selector_str = selector_item
                if "://" in selector_item: # e.g., "xpath://foo" or "css://bar" (though css prefix isn't standard)
                    try:
                        sel_type, sel_val = selector_item.split("://", 1)
                        if sel_type.lower() == 'xpath':
                            search_params_for_dom['xpath'] = sel_val
                        else: # default to css if unknown prefix or "css://"
                            search_params_for_dom['css'] = sel_val
                    except ValueError:
                         search_params_for_dom['css'] = selector_item # Not a prefixed selector
                else:
                    search_params_for_dom['css'] = selector_item # Assume CSS if no prefix
            elif isinstance(selector_item, dict):
                # If it's a dict, assume it's already in the format find_element_with_retry expects
                # e.g., {"css": "foo", "text": "bar"}
                search_params_for_dom.update(selector_item)
                processed_selector_str = str(selector_item)
            else:
                if log_not_found:
                    self.log.warning(f"Unsupported selector format in list for {group_key}.{element_key}: {selector_item}")
                continue # Try next selector in the list
            
            if not search_params_for_dom:
                if log_not_found:
                    self.log.debug(f"No search parameters derived for selector item: {selector_item} ({group_key}.{element_key}). Skipping this item.")
                continue

            self.log.debug(f"Attempting find_site_element for '{current_logical_name}' using selector {i+1}/{len(selectors_to_try)}: {processed_selector_str}")
            extracted_element_obj = self.dom.find_element_with_retry(
                context_to_search, 
                logical_name=current_logical_name, 
                retries=effective_retries,
                pause_sec=effective_pause_sec,
                log_not_found=False, # We handle final logging here
                shadow_path=shadow_path,
                **search_params_for_dom
            )
            
            if extracted_element_obj and extracted_element_obj.value:
                self.log.info(f"Found site element '{logical_name_base}' using selector item: {processed_selector_str} (Strategy: {extracted_element_obj.found_by_strategy})")
                return extracted_element_obj
        
        if log_not_found:
            self.log.warning(f"Site element '{logical_name_base}' not found with any of the provided selectors: {selector_or_list}")
        return None
    
    def wait_for_site_element(self, driver, group_key: str, element_key: str, timeout: int = None) -> Optional[ExtractedElement]:
        """Wait for site-specific element. Returns an ExtractedElement object or None.
           This method primarily ensures an element is present and interactable within a timeout.
        """
        effective_timeout = timeout if timeout is not None else self.config.default_wait_timeout
        start_time = time.time()
        logical_name = f"{self.site_config.name}_{group_key}_{element_key}_wait"
        
        extracted_obj: Optional[ExtractedElement] = None
        pause_between_wait_checks = self.config.default_retry_pause_sec 

        while time.time() - start_time < effective_timeout:
            current_log_not_found = (time.time() - start_time + pause_between_wait_checks >= effective_timeout)

            extracted_obj = self.find_site_element(driver, 
                                                   group_key, 
                                                   element_key, 
                                                   retries=1, 
                                                   pause_sec=0, 
                                                   log_not_found=current_log_not_found 
                                                  )
            
            if extracted_obj and extracted_obj.value: # Check if an element was found
                if extracted_obj.properties and extracted_obj.properties.is_displayed:
                    self.log.info(f"Waited and found site element '{logical_name}' (selector: {extracted_obj.source_selector}, strategy: {extracted_obj.found_by_strategy}). Returning ExtractedElement.")
                    return extracted_obj # Return the ExtractedElement object
                elif not extracted_obj.properties:
                    self.log.debug(f"Element '{logical_name}' found, but properties (like is_displayed) are missing. Assuming visible and returning ExtractedElement.")
                    return extracted_obj # Return the ExtractedElement object
                else:
                    self.log.debug(f"Element '{logical_name}' found but not displayed/interactable. Displayed: {extracted_obj.properties.is_displayed}. Continuing wait.")
            
            if time.time() - start_time + pause_between_wait_checks >= effective_timeout:
                break 
            time.sleep(pause_between_wait_checks)
        
        self.log.warning(f"Timed out waiting for site element '{logical_name}' after {effective_timeout}s. Last selector tried: {extracted_obj.source_selector if extracted_obj else 'N/A'}")
        return None # Return None if not found or not ready within timeout
    
    def extract_search_results(self, driver) -> List[Dict[str, Any]]:
        """Extract search results in a standardized format"""
        results = []
        
        try:
            # This should be overridden by specific site modules
            content = self.dom.extract_content(driver, 'structured')
            
            # Generic fallback
            results.append({
                'title': content.get('title', ''),
                'url': content.get('url', ''),
                'text': content.get('text', '')[:500] + '...' if len(content.get('text', '')) > 500 else content.get('text', ''),
                'source': self.site_config.name
            })
            
        except Exception as e:
            self.log.error(f"Failed to extract search results: {e}")
        
        return results
    
    def apply_site_specific_delays(self) -> None:
        """Apply site-specific timing delays"""
        site_delays = self.site_config.timeouts
        
        if 'page_load' in site_delays:
            self.behavior.thinking_pause()
        
        if 'between_actions' in site_delays:
            delay = site_delays['between_actions']
            self.behavior.human_pause(delay, delay * 1.5)

    def is_driver_active_from_module(self) -> bool:
        """Checks if the WebDriver instance is active and responsive."""
        if not self.driver:
            self.log.debug("Driver not active: No driver instance.")
            return False
        try:
            _ = self.driver.current_url # A lightweight operation to check driver responsiveness
            return True
        except Exception as e: # Catches various selenium errors if driver is dead (e.g., WebDriverException)
            self.log.warning(f"Driver not active: Exception during health check: {type(e).__name__} - {e}")
            return False


class SiteRegistry:
    """Registry for managing site-specific modules"""
    
    def __init__(self):
        self._modules = {}
    
    def register(self, site_name: str, module_class: type) -> None:
        """Register a site module"""
        self._modules[site_name] = module_class
    
    def get_module(self, site_name: str, **kwargs) -> Optional[BaseSiteModule]:
        """Get a site module instance"""
        if site_name not in self._modules:
            return None
        
        module_class = self._modules[site_name]
        return module_class(**kwargs)
    
    def list_supported_sites(self) -> List[str]:
        """List all supported sites"""
        return list(self._modules.keys())


# Global registry instance
site_registry = SiteRegistry() 