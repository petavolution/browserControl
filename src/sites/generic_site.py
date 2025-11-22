"""
Generic Site Module for BrowserControL01
=========================================

Handles interactions with arbitrary web pages when no specific site module is available.
This module effectively replaces the former TextIOWorkflow.
"""

import time
import pathlib
from typing import Dict, Any, Optional, List, Union

from .base_site import BaseSiteModule, site_registry
from core.config import SiteConfig, SystemConfig
from core.structures import ExtractedElement
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from utils.logger import StealthLogger


class GenericSiteModule(BaseSiteModule):
    """Site module for interacting with generic web pages."""

    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: StealthLogger,
                 site_config: Optional[SiteConfig] = None, **kwargs):
        # Generic site doesn't rely on a specific selector file by default.
        # Base URL is not fixed, it will be provided per operation.
        # Use provided site_config or create a default one for generic operations
        effective_site_config = site_config or SiteConfig(name="GenericSite", base_url="")

        super().__init__(driver=driver, config=config, logger=logger,
                         site_config=effective_site_config, **kwargs)
        self.driver = driver
        self.log.info("GenericSiteModule initialized with a managed WebDriver.")

    def interact(self, url: str, input_text: Optional[str] = None, 
                   input_selectors: Optional[List[str]] = None, 
                   click_selectors: Optional[List[str]] = None, 
                   extraction_config: Optional[Dict[str, Any]] = None, 
                   **params) -> Dict[str, Any]:
        """
        Main interaction method for generic pages. 
        Navigates to a URL, optionally types text, clicks elements, and extracts content.

        Args:
            url: The URL to interact with.
            input_text: Text to type into input fields found by input_selectors.
            input_selectors: List of CSS selectors for input fields.
            click_selectors: List of CSS selectors for elements to click after inputting text.
            extraction_config: Configuration for content extraction. Example:
                {
                    "type": "text" | "structured" | "all", (default: "text")
                    "custom_selectors": ["div.article", "p.summary"], (optional)
                    "elements_to_extract": [{"name": "title", "selector": "h1.main-title"}] (for structured)
                }
            params: Additional parameters (e.g., profile).
        """
        profile_name = params.get('profile', self.config.current_profile_name)
        current_url_for_error = url # Initial URL for error reporting
        
        self.log.info(f"Generic interaction started for URL: {url}")
        if input_text: self.log.info(f"Input text provided: {input_text[:50]}...")
        if input_selectors: self.log.info(f"Input selectors: {input_selectors}")
        if click_selectors: self.log.info(f"Click selectors: {click_selectors}")
        if extraction_config: self.log.info(f"Extraction config: {extraction_config}")

        try:
            # Removed: with self.browser_manager.session_context(profile_name) as driver:
            # We now use self.driver which is passed in.
            if not self.driver or not self.is_driver_active_from_module(): # Check if driver is usable
                return self._create_error_result("Browser driver is not active or available", current_url_for_error)
                
            self.log.info(f"Navigating to: {url} using managed driver.")
            self.driver.get(url)
            self.wait_for_page_ready(self.driver) # Pass self.driver
            current_url_for_error = self.driver.current_url
            self.log.info(f"Successfully navigated to: {current_url_for_error}")

            self.behavior.prompt_for_manual_intervention("After navigation to generic URL")

            # Handle text input
            if input_text and input_selectors:
                for i, selector in enumerate(input_selectors):
                    self.log.info(f"Attempting to input text into element matching: {selector}")
                    element_to_type = self.dom.find_element(self.driver, logical_name=f"generic_input_{i}", css=selector) # Pass self.driver
                    if element_to_type and element_to_type.value:
                        self.behavior.clear_and_type(element_to_type.value, input_text, speed="normal")
                        self.log.info(f"Typed text into: {selector}")
                        self.behavior.human_pause(0.2, 0.5)
                    else:
                        self.log.warning(f"Could not find input element: {selector}")
            elif input_text and not input_selectors:
                self.log.warning("Input text provided, but no input_selectors specified. Text will not be typed.")

            self.behavior.prompt_for_manual_intervention("After text input on generic URL")

            # Handle clicks
            if click_selectors:
                for i, selector in enumerate(click_selectors):
                    self.log.info(f"Attempting to click element matching: {selector}")
                    element_to_click = self.dom.find_element(self.driver, logical_name=f"generic_click_{i}", css=selector) # Pass self.driver
                    if element_to_click and element_to_click.value:
                        self.behavior.human_click(element_to_click.value)
                        self.log.info(f"Clicked element: {selector}")
                        self.wait_for_page_ready(self.driver) # Wait for potential page load after click; Pass self.driver
                        current_url_for_error = self.driver.current_url
                    else:
                        self.log.warning(f"Could not find element to click: {selector}")
            
            self.behavior.prompt_for_manual_intervention("After clicks on generic URL")

            # Handle content extraction
            extracted_data: Optional[Dict[str, Any]] = None
            # Default to 'article' extraction if no specific config, or if 'all' is requested.
            # 'text' and 'structured' in extraction_config will also map to 'article' for simplicity now.
            extract_type_from_config = (extraction_config or {}).get("type", "article") 
            final_extract_type_for_dom = 'article' # Default to our best generic extraction

            if extract_type_from_config in ['article', 'structured', 'text', 'all']:
                # For generic sites, 'text', 'structured', and 'all' will now all leverage the 'article' extraction logic
                # as it provides a comprehensive and structured output.
                self.log.info(f"Performing '{final_extract_type_for_dom}' extraction for {self.driver.current_url}")
                extracted_data = self.dom.extract_content(
                    self.driver, 
                    content_type=final_extract_type_for_dom, 
                    base_url=self.driver.current_url
                )
                if extracted_data and isinstance(extracted_data, dict) and extracted_data.get("error"):
                    self.log.error(f"Error during '{final_extract_type_for_dom}' extraction: {extracted_data.get('error')}")
                elif extracted_data:
                    self.log.info(f"Successfully performed '{final_extract_type_for_dom}' extraction. Article title: {extracted_data.get('article_title')}")
                else:
                    self.log.warning(f"'{final_extract_type_for_dom}' extraction returned no data.")
            else:
                self.log.warning(f"Unsupported extraction_config type: '{extract_type_from_config}'. No content will be extracted.")

            return self._create_success_result(data={
                'url': self.driver.current_url,
                'input_text_used': input_text is not None and input_selectors is not None,
                'clicks_performed': click_selectors is not None,
                'extraction_type_requested': extract_type_from_config,
                'content': extracted_data if extracted_data else {}
            })

        except Exception as e:
            # self.log.error is automatically called by _create_error_result in BaseSiteModule
            # self.log.error(f"Generic site interaction failed for URL {url}: {e}", exc_info=True) # Keep this specific log if exc_info is valuable
            return self._create_error_result(error_message=f"Generic interaction failed: {type(e).__name__} - {e}", current_url=current_url_for_error, details=str(e))

    # Override default operations not relevant for GenericSite
    def search(self, query: str, **params) -> Dict[str, Any]:
        # self.log.warning is now handled by _create_error_result logging
        return self._create_error_result(error_message="'search' is not a standard operation for GenericSiteModule.", current_url=params.get('url', ''))

    def browse(self, category: Optional[str] = None, **params) -> Dict[str, Any]:
        # self.log.warning is now handled by _create_error_result logging
        return self._create_error_result(error_message="'browse' is not a standard operation for GenericSiteModule.", current_url=params.get('url', ''))

    def validate_params(self, **params) -> bool:
        """GenericSiteModule's interact operation does not require a 'query' parameter.
           Other parameters like 'url' are validated within the interact method itself if necessary.
        """
        # For generic 'interact', 'url' is the key. 'query' is not typically used.
        # If 'url' is needed, the 'interact' method itself should check.
        # This base validation is now permissive for GenericSiteModule.
        return True

# Register module
site_registry.register('generic', GenericSiteModule) 