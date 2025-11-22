#!/usr/bin/env python3
"""
Google Search Module for BrowserControL01
==========================================

Optimized automation for Google Search with advanced result extraction.
"""

import time
from typing import Dict, Any, List, Optional
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

# Local/Project-specific imports
from .base_site import BaseSiteModule, site_registry
from core.config import SiteConfig, SystemConfig # For type hints
from core.structures import ExtractedElement # Changed
import undetected_chromedriver as uc # For driver type hint
from logging import Logger # For logger type hint


class GoogleSearchModule(BaseSiteModule):
    """Google Search specialized automation module, inheriting from BaseSiteModule"""
    
    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: Logger, site_config: SiteConfig, **kwargs):
        # SiteConfig is now passed in.
        super().__init__(driver=driver, config=config, logger=logger, site_config=site_config, **kwargs)
        self.driver = driver # Store managed driver
        self.log.info(f"GoogleSearchModule initialized with managed WebDriver. Site config name: {self.site_config.name}")

    def search(self, query: str, **params) -> Dict[str, Any]:
        """Perform Google search with result extraction"""
        # profile_name is handled by BrowserControlSystem when getting the driver
        # driver instance is now self.driver
        max_results = params.get('max_results', self.site_config.custom_params.get('max_results_default', 10))
        extract_snippets = params.get('extract_snippets', self.site_config.custom_params.get('extract_snippets_default', True))
        
        current_url_for_error: Optional[str] = self.site_config.base_url

        try:
            # Removed: with self.browser_manager.session_context(profile_name) as driver:
            if not self.driver or not self.is_driver_active_from_module(): # Check if driver is usable
                return self._create_error_result(error_message="Browser driver is not active or available")
                
            current_url_for_error = self.driver.current_url

            if not self._navigate_to_google(self.driver):
                return self._create_error_result(error_message="Failed to navigate to Google", current_url=self.driver.current_url)
            current_url_for_error = self.driver.current_url
            self.wait_for_page_ready(self.driver) 
            
            self._handle_consent_popup(self.driver)
            current_url_for_error = self.driver.current_url
            
            if not self._perform_search_action(self.driver, query):
                return self._create_error_result(error_message="Failed to perform search action", current_url=self.driver.current_url)
            current_url_for_error = self.driver.current_url
            
            if not self._wait_for_search_results_page(self.driver):
                self.log.warning("Wait for search results page indicated potential issues, but proceeding to extraction.")
            current_url_for_error = self.driver.current_url
            
            results = self._extract_google_results(self.driver, max_results, extract_snippets)
            
            if not results:
                did_you_mean_ext = self.find_site_element(
                    self.driver, # Use self.driver
                    group_key="results_page",
                    element_key="did_you_mean_selector",
                    retries=1, 
                    log_not_found=False
                )
                if did_you_mean_ext and did_you_mean_ext.value:
                    suggestion_text = did_you_mean_ext.value.text
                    self.log.info(f"No direct results. Google suggested: '{suggestion_text}'")
                    return self._create_success_result(
                        data={'query': query, 'results_count': 0, 'results': [], 'suggestion': suggestion_text, 'search_url': self.driver.current_url},
                        message=f"No direct results found. Suggestion: {suggestion_text}"
                    )

            return self._create_success_result(data={
                'query': query,
                'results_count': len(results),
                'results': results,
                'search_url': self.driver.current_url
            })
                
        except Exception as e:
            self.log.error(f"Google search workflow failed: {e}", exc_info=True)
            final_url_on_error: Optional[str] = current_url_for_error
            # Check self.driver directly, not a local 'driver' variable
            if self.driver:
                try:
                    final_url_on_error = self.driver.current_url
                except Exception: pass

            return self._create_error_result(error_message=f"Google search failed: {str(e)}", current_url=final_url_on_error)
    
    def _navigate_to_google(self, driver) -> bool:
        """Navigate to Google homepage using BaseSiteModule's navigation"""
        return self.navigate_to_site(driver) # Uses self.site_config.base_url
    
    def _handle_consent_popup(self, driver) -> None:
        """Handle Google's consent popup if present using selectors from JSON"""
        self.log.debug("Checking for Google consent popup...")
        initial_wait = self.site_config.timeouts.get('consent_popup_wait_initial', 1.0)
        time.sleep(initial_wait) # Allow some time for popup to potentially load

        dialog_present_ext = self.find_site_element(driver, 
                                                    group_key="consent_page", 
                                                    element_key="dialog_identifier_selector",
                                                    retries=1, 
                                                    pause_sec=0.2, 
                                                    log_not_found=False)
        if not (dialog_present_ext and dialog_present_ext.value):
            self.log.info("Consent dialog identifier not found via find_site_element. Assuming no popup or already handled.")
            return

        accept_button_selectors_list = self.get_selector("consent_page", "accept_buttons_selectors") # Keep this to iterate
        if not isinstance(accept_button_selectors_list, list):
            accept_button_selectors_list = [accept_button_selectors_list] if accept_button_selectors_list else []

        clicked = False
        # Instead of passing each selector string to find_element_with_retry, 
        # find_site_element can take a list directly if the JSON selector is a list.
        # For this case, accept_buttons_selectors in JSON IS a list.
        # So we can call find_site_element once with that key.
        
        # We need to iterate if the JSON provides a LIST of different logical selectors for the same action (e.g. multiple distinct buttons for "accept")
        # The current find_site_element will try a list of actual CSS/XPath strings IF the JSON *value* for a single key is a list.
        # Here, "accept_buttons_selectors" is a key whose *value* is a list of strings, each a distinct selector.
        # So, we should call find_site_element for each item in that list.

        # Let's assume for now that get_selector for "accept_buttons_selectors" returns a list of individual selectors to try one by one.
        # Or, if find_site_element were enhanced to take a *list of element_keys* that might be another path.
        # The current find_site_element expects ONE element_key, which might resolve to a list of selector strings.

        # Sticking to the pattern: get_selector gets the list of strings, then iterate and call find_site_element for each *string*.
        # No, this is wrong. find_site_element itself handles a list of selector strings if get_selector(group, key) returns a list.
        # The JSON for accept_buttons_selectors IS a list of strings. So find_site_element for "accept_buttons_selectors" should work.

        consent_btn_ext = self.find_site_element(driver, 
                                               group_key="consent_page", 
                                               element_key="accept_buttons_selectors", # This key in JSON points to a list of selectors
                                               retries=self.site_config.custom_params.get('consent_check_retries', 1),
                                               pause_sec=self.site_config.custom_params.get('consent_check_pause', 0.5),
                                               log_not_found=False)

        if consent_btn_ext and consent_btn_ext.value and consent_btn_ext.properties and consent_btn_ext.properties.is_displayed:
            self.log.info(f"Consent button found with composite selector key 'accept_buttons_selectors'. Matched selector: {consent_btn_ext.source_selector}. Attempting click.")
            self.behavior.human_click(consent_btn_ext.value)
            self.behavior.human_pause(
                self.site_config.timeouts.get('consent_popup_wait_after_action', 0.5),
                self.site_config.timeouts.get('consent_popup_wait_after_action', 0.5) * 1.5
            )
            self.wait_for_page_ready(driver, timeout=5)
            clicked = True
            self.log.info("Clicked a consent button.")
        
        if clicked:
            self.log.info("Consent popup handled.")
        else:
            self.log.info("No actionable consent buttons found from the provided selectors, or dialog not identified.")

    def _find_search_input_element(self, driver) -> Optional[ExtractedElement]:
        """Find Google search input field using selectors from JSON"""
        # search_input_selectors in JSON is a list of individual selectors.
        # find_site_element will try each of them.
        search_input_ext = self.find_site_element(driver, 
                                                group_key="search_page", 
                                                element_key="search_input_selectors",
                                                retries=self.site_config.custom_params.get('search_input_retries', 2),
                                                pause_sec=self.site_config.custom_params.get('search_input_pause', 0.5),
                                                log_not_found=True) # Log if not found after all attempts
        
        if search_input_ext and search_input_ext.value:
            self.log.info(f"Found Google search input with key 'search_input_selectors'. Matched selector: {search_input_ext.source_selector}")
            return search_input_ext
        
        # log_not_found=True in find_site_element call handles the warning if null
        return None
    
    def _perform_search_action(self, driver, query: str) -> bool:
        """Execute the search query using elements found via JSON selectors"""
        self.log.info(f"Performing Google search for: {query}")
        
        search_input_ext = self._find_search_input_element(driver)
        if not (search_input_ext and search_input_ext.value):
            return False # Error already logged by _find_search_input_element
        
        self.behavior.clear_and_type(search_input_ext.value, query, "normal")
        self.behavior.human_pause(0.3, 0.8) # Pause after typing

        submitted_by_click = False # Initialize to False
        search_button_ext = self.find_site_element(driver,
                                                 group_key="search_page",
                                                 element_key="search_button_after_type_selectors",
                                                 retries=1, 
                                                 log_not_found=False) # Okay if not found, will press Enter
                                                 
        if search_button_ext and search_button_ext.value and search_button_ext.properties and search_button_ext.properties.is_displayed:
            self.log.info(f"Attempting to click search button (key 'search_button_after_type_selectors'). Matched selector: {search_button_ext.source_selector}")
            self.behavior.human_click(search_button_ext.value)
            submitted_by_click = True
        
        if not submitted_by_click:
            self.log.info("Search button not found or not clicked, pressing Enter in search input.")
            self.behavior.press_key(search_input_ext.value, Keys.RETURN)
        
        self.wait_for_page_ready(driver, timeout=self.site_config.timeouts.get('search_results_load_timeout', 15))
        return True
    
    def _wait_for_search_results_page(self, driver) -> bool:
        """Wait for Google search results to load using selectors from JSON"""
        self.log.debug("Waiting for Google search results page to load...")
        results_container_selector = self.get_selector("results_page", "results_container_selector")
        if not results_container_selector:
            self.log.error("Results container selector not defined in config. Cannot wait for results.")
            return False
        
        # Wait for results container using wait_for_site_element
        # wait_for_site_element internally uses self.get_selector, so we pass keys
        # wait_for_site_element now returns ExtractedElement
        container_ext = self.wait_for_site_element(driver, 
                                                        group_key='results_page', 
                                                        element_key='results_container_selector', 
                                                        timeout=self.site_config.timeouts.get('search_results_container_wait', 10))
        
        if not (container_ext and container_ext.value):
            self.log.warning("Google search results container did not appear in time.")
            # Check for "No results" message as a possible valid outcome
            no_results_msg_selector_key = "no_results_message_selector" # Define key for clarity
            # Check if this key exists in JSON first using get_selector to avoid errors if not defined.
            if self.get_selector("results_page", no_results_msg_selector_key):
                 no_results_ext = self.find_site_element(driver, 
                                                          group_key="results_page", 
                                                          element_key=no_results_msg_selector_key, 
                                                          retries=0, 
                                                          log_not_found=False)
                 if no_results_ext and no_results_ext.value:
                      self.log.info("Search results page loaded, but indicates no results based on 'no_results_message_selector'.")
                      return True # Page is loaded, even if no results.
            return False

        # Additional pause for results to populate within the container
        time.sleep(self.site_config.timeouts.get('search_results_populate_wait', 1.0))
        self.log.info("Google search results page appears to be loaded.")
        return True
    
    def _extract_google_results(self, driver, max_results: int, extract_snippets: bool) -> List[Dict[str, Any]]:
        """Extract Google search results using extract_item_details_from_list"""
        self.log.debug(f"Extracting up to {max_results} Google results. Snippets: {extract_snippets}")

        results_container_selector = self.get_selector('results_page', 'results_container_selector')
        result_item_selector = self.get_selector('results_page', 'result_item_selector')

        if not results_container_selector or not result_item_selector:
            self.log.error("Missing essential selectors for Google results extraction (container or item).")
            return []

        # The container for extract_item_details_from_list is where items are direct children.
        # For Google, result_item_selector usually finds items *within* results_container_selector.
        # So, the effective item selector to pass to extract_item_details_from_list should target
        # the individual result items directly.
        # We assume result_item_selector is relative to the driver or document root.
        # If result_item_selector is meant to be *inside* results_container_selector, 
        # then we should provide results_container_selector + " " + result_item_selector, or similar logic.
        # For now, assuming result_item_selector is globally sufficient for find_elements.
        
        # Let's adjust: extract_item_details_from_list expects a container *from which to find items*.
        # For Google, the `div.g` are the items themselves, typically found within `#search`.
        # The `container_selector` for `extract_item_details_from_list` should be the `result_item_selector`.
        
        item_detail_config = {
            'title': {
                'selector': self.get_selector('results_page', 'item_title_selector'),
                'type': 'text',
                'is_required': True
            },
            'url': { # For the URL, we need the href from the anchor often wrapping or being the title
                'selector': self.get_selector('results_page', 'item_url_anchor_selector'),
                'type': 'attribute:href', # Special type to get 'href' attribute
                'is_required': True
            }
        }
        if extract_snippets:
            # item_snippet_selectors can be a list. We need to handle this.
            # extract_item_details_from_list expects a single selector string for each detail.
            # We will need to pick one or adapt extract_item_details_from_list later.
            # For now, let's assume the first snippet selector is primary.
            snippet_selectors_val = self.get_selector('results_page', 'item_snippet_selectors')
            primary_snippet_selector = None
            if isinstance(snippet_selectors_val, list) and snippet_selectors_val:
                primary_snippet_selector = snippet_selectors_val[0]
            elif isinstance(snippet_selectors_val, str):
                primary_snippet_selector = snippet_selectors_val
            
            if primary_snippet_selector:
                 item_detail_config['snippet'] = {
                    'selector': primary_snippet_selector,
                    'type': 'text',
                    'is_required': False
                }
            else:
                self.log.warning("No snippet selector found or configured for Google results.")


        # The `container_selector` for extract_item_details_from_list should point to the *individual items*.
        # `result_item_selector` from our JSON ("div.g") is this.
        raw_extracted_items: List[Dict[str, ExtractedElement]] = self.dom.extract_item_details_from_list(
            driver,
            container_selector=result_item_selector, # This is key: it identifies each repeating search result block
            item_detail_selectors=item_detail_config,
            max_items=max_results
        )

        processed_results: List[Dict[str, Any]] = []
        for idx, item_data_map in enumerate(raw_extracted_items):
            # item_data_map is Dict[str, ExtractedElement]
            title_ext = item_data_map.get('title')
            url_ext = item_data_map.get('url')
            
            title = title_ext.value if title_ext and title_ext.extraction_successful else None
            url = url_ext.value if url_ext and url_ext.extraction_successful else None

            if not (title and url):
                self.log.debug(f"Skipping Google result item {idx+1} due to missing title or URL.")
                continue

            single_result = {
                'position': idx + 1,
                'title': title,
                'url': url,
                'snippet': None # Default to None
                # 'raw_details': item_data_map # Optionally include for debugging
            }

            if extract_snippets:
                snippet_ext = item_data_map.get('snippet')
                if snippet_ext and snippet_ext.extraction_successful:
                    single_result['snippet'] = snippet_ext.value
                elif 'snippet' in item_detail_config: # If we tried to extract it but failed
                     self.log.debug(f"Snippet extraction failed for item {idx+1}: {title}")


            processed_results.append(single_result)
            self.log.debug(f"Processed Google result: {title[:60]}...")
            
        self.log.info(f"Extracted {len(processed_results)} Google search results items.")
        return processed_results

# Register module with the global registry
site_registry.register('google', GoogleSearchModule) 