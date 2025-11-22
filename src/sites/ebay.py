#!/usr/bin/env python3
"""
eBay Search Module for BrowserControL01
=======================================

Optimized automation for eBay with auction and product search capabilities.
"""

from typing import Dict, Any, List, Optional
from .base_site import BaseSiteModule, site_registry
from core.config import SiteConfig, SystemConfig
from core.structures import ExtractedElement
# from core.semantic_analyzer import SemanticAnalyzer # Not used in Ebay module currently
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import undetected_chromedriver as uc
from utils.logger import StealthLogger


class EbaySearchModule(BaseSiteModule):
    """eBay Search specialized automation module"""
    
    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: StealthLogger, site_config: SiteConfig, **kwargs):
        super().__init__(driver=driver, config=config, logger=logger, site_config=site_config, **kwargs)
        self.driver = driver
        self.log.info(f"EbaySearchModule initialized with managed WebDriver. Site: {self.site_config.name}")
    
    def search(self, query: str, **params) -> Dict[str, Any]:
        """Perform eBay item search"""
        self.log.info(f"Starting eBay search for: {query}")

        # profile_name = params.get('profile', "default") # Handled by BrowserControlSystem
        max_results = params.get('max_results', self.site_config.custom_params.get('max_results_default', 10))
        current_url_for_error: Optional[str] = self.site_config.base_url

        try:
            # with self.browser_manager.session_context(profile_name) as driver:
            if not self.driver or not self.is_driver_active_from_module():
                return self._create_error_result(error_message="Browser driver is not active or available for eBay search", current_url=current_url_for_error)

            if not self.navigate_to_site(self.driver): # Use self.driver
                current_url_for_error = self.driver.current_url if self.driver else self.site_config.base_url
                return self._create_error_result(error_message="Failed to navigate to eBay", current_url=current_url_for_error)
            current_url_for_error = self.driver.current_url

            self.wait_for_page_ready(self.driver)
            current_url_for_error = self.driver.current_url

            search_input_ext = self.find_site_element(self.driver, 'search_page', 'search_input')
            if not (search_input_ext and search_input_ext.value):
                return self._create_error_result(error_message="Could not locate eBay search input field", current_url=current_url_for_error)
            
            self.behavior.human_type(search_input_ext.value, query, speed='normal')
            self.behavior.human_pause(0.5, 1.0)

            search_button_ext = self.find_site_element(self.driver, 'search_page', 'search_button', log_not_found=False)
            if not (search_button_ext and search_button_ext.value):
                self.log.warning("eBay search button not found via find_site_element, trying Enter key.")
                self.behavior.press_key(search_input_ext.value, Keys.RETURN)
            else:
                self.behavior.human_click(search_button_ext.value)
            current_url_for_error = self.driver.current_url # After action
            
            self.behavior.thinking_pause()
            self.wait_for_page_ready(self.driver)

            results_container_timeout = self.site_config.timeouts.get('results_load_timeout', 20)
            results_container_ext = self.wait_for_site_element(self.driver, 'results_page', 'results_container', timeout=results_container_timeout)

            if not (results_container_ext and results_container_ext.value):
                current_url_for_error = self.driver.current_url 
                no_results_element_ext = self.find_site_element(self.driver, 
                                                                    'results_page', 
                                                                    'no_results_message_selector', 
                                                                    retries=0, 
                                                                    log_not_found=False)
                if no_results_element_ext and no_results_element_ext.value:
                    self.log.info("eBay returned no exact matches for the query.")
                    return self._create_success_result(data={
                        'query': query,
                        'results_count': 0,
                        'results': [],
                        'search_url': current_url_for_error
                    }, message="No exact matches found for the query.")
                return self._create_error_result(error_message="eBay search results did not load (container not found)", current_url=current_url_for_error)
            current_url_for_error = self.driver.current_url

            results = self._extract_ebay_results(self.driver, max_results)
            
            return self._create_success_result(data={
                'query': query,
                'results_count': len(results),
                'results': results,
                'search_url': self.driver.current_url
            })

        except Exception as e:
            self.log.error(f"eBay search workflow failed: {e}", exc_info=True) 
            final_url_on_error: Optional[str] = current_url_for_error # Default to last known
            if self.driver: # Check self.driver
                try: final_url_on_error = self.driver.current_url
                except Exception: pass 
            return self._create_error_result(error_message=f"eBay search failed: {type(e).__name__} - {str(e)}", current_url=final_url_on_error)

    def _extract_ebay_results(self, driver, max_results: int) -> List[Dict[str, Any]]:
        """Extract item information from eBay search results page."""
        self.log.debug(f"Attempting to extract up to {max_results} eBay results using generalized extractor.")

        # Get the container selector(s). This can be a string or a list of strings.
        results_container_selectors = self.get_selector('results_page', 'results_container')

        if not results_container_selectors:
            self.log.error("eBay results_container selector(s) not found. Cannot extract.")
            return []
        
        if not isinstance(results_container_selectors, (str, list)):
            self.log.error(f"eBay results_container selector is of unexpected type: {type(results_container_selectors)}. Cannot extract.")
            return []

        item_detail_selectors = {
            'title': {
                'selector': self.get_selector('results_page', 'item_title'), 
                'type': 'text', 
                'is_required': True
            },
            'url': {
                'selector': self.get_selector('results_page', 'item_url_anchor'), 
                'type': 'attribute:href', 
                'is_required': True
            },
            'price': {
                'selector': self.get_selector('results_page', 'item_price'), 
                'type': 'text', 
                'is_required': False
            },
            'condition': {
                'selector': self.get_selector('results_page', 'item_condition'), 
                'type': 'text',
                'is_required': False
            }
        }
        
        for key, detail_config in item_detail_selectors.items():
            if not detail_config['selector']:
                self.log.error(f"Missing selector for item detail '{key}' in eBay results. Extraction might fail or be incomplete.")
                if detail_config.get('is_required', False):
                    self.log.error(f"Required selector for '{key}' is missing. Aborting eBay extraction.")
                    return []

        # extract_item_details_from_list now returns List[Dict[str, ExtractedElement]]
        raw_extracted_item_dicts = self.dom.extract_item_details_from_list(
            driver,
            container_selector=results_container_selectors, 
            item_detail_selectors=item_detail_selectors,
            max_items=max_results
        )
        
        processed_results: List[Dict[str, Any]] = []
        for idx, item_details_map in enumerate(raw_extracted_item_dicts):
            # item_details_map is Dict[str, ExtractedElement]
            current_processed_item: Dict[str, Any] = {
                'position': idx + 1,
                'details': {} # Store ExtractedElement objects
            }

            # Store all ExtractedElement objects
            for detail_name, ext_elem in item_details_map.items():
                current_processed_item['details'][detail_name] = ext_elem

            # --- Populate convenience fields ---
            title_ext_elem = item_details_map.get('title')
            if title_ext_elem and title_ext_elem.extraction_successful:
                current_processed_item['title'] = title_ext_elem.value
            else:
                current_processed_item['title'] = "[Extraction Failed]"
                self.log.warning(f"Title extraction failed or element not found for eBay item at position {idx + 1}.")

            url_ext_elem = item_details_map.get('url')
            current_processed_item['url'] = None # Initialize
            if url_ext_elem and url_ext_elem.extraction_successful and isinstance(url_ext_elem.value, str):
                url_value = url_ext_elem.value
                if not url_value.startswith('http'):
                    if url_value.startswith('//'):
                        current_processed_item['url'] = "https:" + url_value
                    elif url_value.startswith('/'):
                        current_processed_item['url'] = self.site_config.base_url + url_value
                    else:
                        current_processed_item['url'] = url_value 
                else:
                    current_processed_item['url'] = url_value
            elif title_ext_elem and not current_processed_item['title'] == "[Extraction Failed]":
                self.log.debug(f"URL not extracted or extraction failed for eBay item: {current_processed_item.get('title')}")

            price_ext_elem = item_details_map.get('price')
            if price_ext_elem and price_ext_elem.extraction_successful:
                current_processed_item['price'] = price_ext_elem.value
            else:
                current_processed_item['price'] = "N/A"

            condition_ext_elem = item_details_map.get('condition')
            if condition_ext_elem and condition_ext_elem.extraction_successful:
                current_processed_item['condition'] = condition_ext_elem.value
            else:
                current_processed_item['condition'] = "N/A"

            if current_processed_item.get('title') and current_processed_item.get('url') and current_processed_item['title'] != "[Extraction Failed]":
                processed_results.append(current_processed_item)
                self.log.debug(f"Processed eBay item for output: {current_processed_item['title'][:50]}...")
            elif current_processed_item['title'] != "[Extraction Failed]":
                self.log.debug(f"Skipping eBay item for output due to missing title or URL: {current_processed_item.get('title', '[No Title]')}")
        
        self.log.info(f"Successfully processed {len(processed_results)} eBay products for final output structure.")
        return processed_results

# Register the eBay module
site_registry.register('ebay', EbaySearchModule) 