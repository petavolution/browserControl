#!/usr/bin/env python3
"""
Amazon Search Module for BrowserControL01
==========================================

Optimized automation for Amazon with product search capabilities.
"""

from typing import Dict, Any, List, Optional
from .base_site import BaseSiteModule, site_registry
from core.config import SiteConfig, SystemConfig
from core.structures import ExtractedElement
from core.semantic_analyzer import SemanticAnalyzer
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from logging import Logger


class AmazonSearchModule(BaseSiteModule):
    """Amazon Search specialized automation module"""
    
    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: Logger, site_config: SiteConfig, **kwargs):
        super().__init__(driver=driver, config=config, logger=logger, site_config=site_config, **kwargs)
        self.driver = driver
        self.semantic_analyzer = SemanticAnalyzer(logger=self.log)
        self.log.info(f"AmazonSearchModule initialized with managed WebDriver. Site: {self.site_config.name}")
    
    def search(self, query: str, **params) -> Dict[str, Any]:
        """Perform Amazon product search"""
        self.log.info(f"Starting Amazon search for: {query}")

        max_results = params.get('max_results', self.site_config.custom_params.get('max_results_default', 10))
        current_url_for_error: Optional[str] = self.site_config.base_url

        try:
            if not self.driver or not self.is_driver_active_from_module():
                return self._create_error_result(error_message="Browser driver is not active or available for Amazon search", current_url=current_url_for_error)

            if not self.navigate_to_site(self.driver):
                current_url_for_error = self.driver.current_url if self.driver else self.site_config.base_url
                return self._create_error_result(error_message="Failed to navigate to Amazon", current_url=current_url_for_error)
            current_url_for_error = self.driver.current_url

            self.wait_for_page_ready(self.driver)
            current_url_for_error = self.driver.current_url

            search_input_ext = self.find_site_element(self.driver, 'search_page', 'search_input')
            if not search_input_ext or not search_input_ext.value:
                return self._create_error_result(error_message="Could not locate Amazon search input field", current_url=current_url_for_error)
            
            self.behavior.human_type(search_input_ext.value, query, speed='normal')
            self.behavior.human_pause(0.5, 1.0)

            search_button_ext = self.find_site_element(self.driver, 'search_page', 'search_button', log_not_found=False)
            if not (search_button_ext and search_button_ext.value):
                self.log.warning("Amazon search button not found via find_site_element, trying Enter key.")
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
                return self._create_error_result(error_message="Amazon search results did not load (container not found)", current_url=current_url_for_error)
            current_url_for_error = self.driver.current_url

            results = self._extract_amazon_results(self.driver, max_results)
            
            return self._create_success_result(data={
                'query': query,
                'results_count': len(results),
                'results': results,
                'search_url': self.driver.current_url
            })

        except Exception as e:
            self.log.error(f"Amazon search workflow failed: {e}", exc_info=True) # Keep exc_info log
            final_url_on_error: Optional[str] = current_url_for_error # Default to last known
            if self.driver: # Check self.driver instead of local 'driver'
                try: final_url_on_error = self.driver.current_url
                except Exception: pass 

            return self._create_error_result(error_message=f"Amazon search failed: {type(e).__name__} - {str(e)}", current_url=final_url_on_error)

    def _extract_amazon_results(self, driver, max_results: int) -> List[Dict[str, Any]]:
        """Extract product information from Amazon search results page using the generalized extractor."""
        self.log.debug(f"Attempting to extract up to {max_results} Amazon results with enhanced generic extractor.")

        # Directly get the selector(s) for the results container.
        # This can be a string or a list of strings, as defined in the JSON selector file.
        # The extract_item_details_from_list method in AdaptiveDOMInteractor now handles this.
        results_container_selectors = self.get_selector('results_page', 'results_container')

        if not results_container_selectors:
            self.log.error("Amazon results_container selector(s) not found. Cannot extract.")
            return []
        
        # Type check, though get_selector should ideally return str, List[str], or None
        if not isinstance(results_container_selectors, (str, list)):
            self.log.error(f"Amazon results_container selector is of unexpected type: {type(results_container_selectors)}. Cannot extract.")
            return []
        
        item_detail_selectors = {
            'title_text': {
                'selector': self.get_selector('results_page', 'product_title'), 
                'type': 'text', 
                'is_required': True
            },
            'title_link_element': {
                'selector': self.get_selector('results_page', 'product_title'), 
                'type': 'element', 
                'is_required': True
            },
            'price_whole': {
                'selector': self.get_selector('results_page', 'product_price_whole'), 
                'type': 'text'
            },
            'price_fraction': {
                'selector': self.get_selector('results_page', 'product_price_fraction'),
                'type': 'text'
            },
            'rating_text': {
                'selector': self.get_selector('results_page', 'product_rating'), 
                'type': 'text'
            }
        }
        
        # Validate that all essential selectors for item_detail_selectors were found
        for key, detail_config in item_detail_selectors.items():
            if not detail_config['selector']:
                self.log.error(f"Missing selector for item detail '{key}' in Amazon results. Extraction might fail or be incomplete.")
                if detail_config.get('is_required', False):
                    self.log.error(f"Required selector for '{key}' is missing. Aborting Amazon extraction.")
                    return []

        # The extract_item_details_from_list method now handles trying multiple container selectors if a list is provided.
        raw_extracted_items: List[Dict[str, ExtractedElement]] = self.dom.extract_item_details_from_list(
            driver,
            container_selector=results_container_selectors, 
            item_detail_selectors=item_detail_selectors,
            max_items=max_results
        )

        processed_results: List[Dict[str, Any]] = [] # Final list of processed items

        for idx, item_details_map in enumerate(raw_extracted_items):
            # item_details_map is Dict[str, ExtractedElement]
            
            # >>> Integrate SemanticAnalyzer here <<<
            # The ExtractedElement objects within item_details_map will be updated in place.
            self.log.debug(f"Performing semantic analysis for Amazon item at position {idx + 1}")
            item_details_map = self.semantic_analyzer.analyze_extracted_item_details(item_details_map)

            # We want to transform this into a more structured final_item for the workflow output.
            # The final_item will store key information, potentially including the ExtractedElement objects themselves
            # or carefully chosen parts of their data for the final JSON output.
            
            current_processed_item: Dict[str, Any] = {
                'position': idx + 1,
                'details': {} # To store the ExtractedElement objects or their representations
            }

            # General handling for all extracted details
            for detail_name, ext_elem in item_details_map.items():
                current_processed_item['details'][detail_name] = ext_elem # Store the whole ExtractedElement

            # --- Post-processing and convenience fields based on ExtractedElement objects ---
            # These convenience fields are what will primarily be used by generic result handlers/loggers
            # The full ExtractedElement objects in 'details' are for richer data access if needed.

            title_ext_elem = item_details_map.get('title_text')
            if title_ext_elem and title_ext_elem.extraction_successful:
                current_processed_item['title'] = title_ext_elem.value
            else:
                current_processed_item['title'] = "[Extraction Failed]"
                self.log.warning(f"Title extraction failed or element not found for Amazon item at position {idx + 1}.")

            # URL extraction (requires special handling of the WebElement in title_link_element)
            current_processed_item['url'] = None # Initialize
            title_link_ext_elem = item_details_map.get('title_link_element')
            if title_link_ext_elem and title_link_ext_elem.extraction_successful and title_link_ext_elem.value:
                title_selenium_element = title_link_ext_elem.value # This is the Selenium WebElement
                try:
                    parent_a = title_selenium_element.find_element(By.XPATH, "./ancestor::a[@href]")
                    url = parent_a.get_attribute('href')
                    if url and not url.startswith('http'):
                        current_processed_item['url'] = self.site_config.base_url + url
                    else:
                        current_processed_item['url'] = url
                except NoSuchElementException:
                    self.log.debug(f"Could not find parent <a> tag for URL for Amazon item: {current_processed_item.get('title')}")
                except Exception as e_url:
                    self.log.warning(f"Error extracting URL for Amazon item '{current_processed_item.get('title')}': {e_url}")
            elif title_ext_elem and not current_processed_item['title'] == "[Extraction Failed]":
                 self.log.debug(f"Title link element not found or extraction failed for Amazon item: {current_processed_item.get('title')}")

            # Price combination
            price_w_ext_elem = item_details_map.get('price_whole')
            price_f_ext_elem = item_details_map.get('price_fraction')
            price_w = price_w_ext_elem.value if price_w_ext_elem and price_w_ext_elem.extraction_successful else None
            price_f = price_f_ext_elem.value if price_f_ext_elem and price_f_ext_elem.extraction_successful else None
            if price_w and price_f:
                current_processed_item['price'] = f"{price_w}.{price_f}"
            elif price_w:
                current_processed_item['price'] = price_w
            else:
                current_processed_item['price'] = "N/A"

            rating_ext_elem = item_details_map.get('rating_text')
            if rating_ext_elem and rating_ext_elem.extraction_successful:
                current_processed_item['rating'] = rating_ext_elem.value
            else:
                current_processed_item['rating'] = "N/A"
            
            # Add to results if essential data (title and URL) is present and title extraction wasn't a failure
            if current_processed_item.get('title') and current_processed_item.get('url') and current_processed_item['title'] != "[Extraction Failed]":
                processed_results.append(current_processed_item)
                self.log.debug(f"Processed Amazon item for output: {current_processed_item['title'][:50]}...")
            elif current_processed_item['title'] != "[Extraction Failed]":
                self.log.debug(f"Skipping Amazon item for output due to missing title or URL: {current_processed_item.get('title', '[No Title]')}")
            # If title extraction failed, it was already logged.

        self.log.info(f"Successfully processed {len(processed_results)} Amazon products for final output structure.")
        return processed_results


# Register the Amazon module
site_registry.register('amazon', AmazonSearchModule) 