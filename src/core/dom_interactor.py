#!/usr/bin/env python3
"""
DOM Interaction System for BrowserControL01
============================================

Intelligent DOM interaction with multiple element finding strategies.
"""

import time
import re
from typing import Optional, Dict, Any, List, Union, Tuple
from urllib.parse import urljoin

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, StaleElementReferenceException
)
from bs4 import BeautifulSoup
from bs4.element import CSS

from .config import SystemConfig
from .structures import ExtractedElement, ElementProperties


class AdaptiveDOMInteractor:
    """Simplified DOM interaction with smart element finding"""
    
    def __init__(self, config: SystemConfig, logger):
        self.config = config
        self.log = logger
        self.element_cache = {}
        
    def find_element_with_retry(self, driver, logical_name: str, 
                                retries: Optional[int] = None, 
                                pause_sec: Optional[float] = None, 
                                log_not_found: bool = True, 
                                shadow_path: Optional[List[str]] = None,
                                **search_params) -> Optional[ExtractedElement]:
        """Attempts to find an element using self.find_element, with retries and pauses.

        Args:
            driver: The WebDriver instance or a specific search context (e.g., a WebElement or ShadowRoot).
            logical_name: A human-readable name for the element, used for logging.
            retries (Optional[int]): Number of retries. Defaults to SystemConfig.default_retry_attempts.
            pause_sec (Optional[float]): Pause duration in seconds between retries. Defaults to SystemConfig.default_retry_pause_sec.
            log_not_found (bool): Whether to log if the element is not found after all retries.
            shadow_path (Optional[List[str]]): Path of CSS selectors for shadow DOM hosts.
            **search_params: Keyword arguments for element search (e.g., css="selector", xpath="//path", text="value").
                             These are passed directly to self.find_element.

        Returns:
            Optional[ExtractedElement]: The found element, or None if not found after retries.
        """
        max_retries = retries if retries is not None else self.config.default_retry_attempts
        actual_pause_sec = pause_sec if pause_sec is not None else self.config.default_retry_pause_sec

        for attempt in range(max_retries):
            element_ext = self.find_element(driver, shadow_path=shadow_path, logical_name=logical_name, **search_params)
            
            if element_ext and element_ext.value: # Check .value as find_element returns ExtractedElement
                if attempt > 0: # Log if found after retries
                    self.log.info(f"Element '{logical_name}' found on attempt {attempt + 1}/{max_retries}.")
                return element_ext
            
            if log_not_found and attempt < max_retries -1: # Log only if more retries are pending
                 self.log.debug(f"Element '{logical_name}' not found (attempt {attempt + 1}/{max_retries}). Retrying after {actual_pause_sec}s. Params: {search_params}")
            
            if attempt < max_retries - 1:
                # It's better to use a more robust pause mechanism if available (e.g., from HumanBehaviorEngine)
                # but for now, a simple time.sleep is used directly in DOMInteractor.
                time.sleep(actual_pause_sec)
        
        if log_not_found:
            self.log.warning(f"Failed to find element '{logical_name}' after {max_retries} attempts with params: {search_params}.")
        return None

    def find_element(self, driver, shadow_path: Optional[List[str]] = None, logical_name: str = "found_element", **search_params) -> Optional[ExtractedElement]:
        """Find element using multiple adaptive strategies, with Shadow DOM support.
        Returns an ExtractedElement object containing the Selenium WebElement and metadata.
        """
        
        current_context = driver
        if shadow_path:
            self.log.debug(f"Traversing shadow DOM path: {shadow_path}")
            for i, host_selector in enumerate(shadow_path):
                try:
                    shadow_host = current_context.find_element(By.CSS_SELECTOR, host_selector)
                    if not shadow_host:
                        self.log.warning(f"Shadow host '{host_selector}' (selector: {host_selector}) not found at depth {i}.")
                        return None
                    current_context = shadow_host.shadow_root
                    if not current_context:
                        self.log.warning(f"Shadow root not found for host '{host_selector}' at depth {i}.")
                        return None
                    self.log.debug(f"Successfully entered shadow root for host: {host_selector}")
                except NoSuchElementException:
                    self.log.warning(f"Shadow host '{host_selector}' (selector: {host_selector}) not found at depth {i} (NoSuchElement).")
                    return None    
                except Exception as e_shadow:
                    self.log.error(f"Error traversing shadow DOM at '{host_selector}' (depth {i}): {e_shadow}")
                    return None
            self.log.debug("Successfully navigated shadow DOM path. Final search context is a shadow root.")

        # Use a cache key that includes the shadow path if present
        # For simplicity, the cache key is based on search_params only for now.
        # A more robust cache would also consider the shadow_path and the context's source.
        cache_key = str(search_params) + logical_name 
        
        if cache_key in self.element_cache:
            try:
                element = self.element_cache[cache_key]
                if self._is_visible(element.value):
                    self.log.debug(f"Element found in cache with params: {search_params}")
                    return element
            except StaleElementReferenceException:
                self.log.debug(f"Stale element from cache for params: {search_params}. Removing.")
                del self.element_cache[cache_key]
        
        self.log.debug(f"Attempting to find element '{logical_name}' with params: {search_params} in context: {type(current_context).__name__}")
        
        selenium_element: Optional[Any] = None
        strategy_used: Optional[str] = None
        final_selector_used: Optional[str] = None

        # Strategy 1: Direct selectors
        self.log.debug("Strategy 1: Trying direct selectors.")
        direct_result = self._try_direct_selectors(current_context, search_params)
        if direct_result:
            selenium_element, final_selector_used = direct_result
            strategy_used = f"direct_selector:{final_selector_used.split('=')[0]}" # e.g. direct_selector:css
            self.log.info(f"Element '{logical_name}' found using {strategy_used} ('{final_selector_used}')")
        
        # Strategy 2: Smart text/attribute matching
        if not selenium_element:
            self.log.debug("Strategy 2: Trying smart matching.")
            smart_result = self._try_smart_matching(current_context, search_params)
            if smart_result:
                selenium_element, match_detail_key = smart_result
                strategy_used = f"smart_matching:{match_detail_key}"
                final_selector_used = f"{search_params.get('type','element')}[{match_detail_key}='{search_params.get(match_detail_key)}']" # Approximate selector
                self.log.info(f"Element '{logical_name}' found using {strategy_used}")
        
        # Strategy 3: Content analysis
        if not selenium_element:
            self.log.debug("Strategy 3: Trying content analysis.")
            content_result = self._try_content_analysis(driver, current_context, search_params)
            if content_result:
                selenium_element, constructed_selector = content_result # Expecting (element, selector_str)
                strategy_used = "content_analysis"
                final_selector_used = constructed_selector if constructed_selector else "content_analysis_match"
                self.log.info(f"Element '{logical_name}' found using content analysis (selector '{final_selector_used}')")
        
        if selenium_element:
            try:
                element_props = ElementProperties(
                    tag_name=selenium_element.tag_name,
                    attributes={attr['name']: attr['value'] for attr in selenium_element.get_property('attributes') if attr['name'] and attr['value']},
                    text=selenium_element.text, 
                    is_displayed=selenium_element.is_displayed(),
                    is_enabled=selenium_element.is_enabled(),
                    location=selenium_element.location,
                    size=selenium_element.size,
                    raw_webelement=selenium_element 
                )
                
                extracted_el = ExtractedElement(
                    name=logical_name,
                    value=selenium_element, # The actual WebElement
                    extraction_type='element',
                    source_selector=final_selector_used or str(search_params),
                    properties=element_props,
                    found_by_strategy=strategy_used,
                    extraction_successful=True
                )
                # self.element_cache[cache_key] = extracted_el # Future caching
                return extracted_el
            except StaleElementReferenceException:
                self.log.warning(f"Element '{logical_name}' became stale immediately after finding with strategy '{strategy_used}'.")
                # Potentially remove from cache if it was added: del self.element_cache[cache_key]
                return None
            except Exception as e_prop_create:
                self.log.error(f"Failed to create ExtractedElement for '{logical_name}' due to: {e_prop_create}", exc_info=True)
                return None
        
        self.log.warning(f"Element '{logical_name}' NOT FOUND with params: {search_params} within the given context.")
        return None
    
    def _try_direct_selectors(self, search_context, params: Dict) -> Optional[Tuple[Any, str]]:
        """Try direct CSS and XPath selectors. Returns (element, selector_string) or None."""
        selectors_tried = []
        for selector_type_key in ['css', 'xpath', 'id', 'class']:
            selector_value = params.get(selector_type_key)
            if not selector_value:
                continue

            is_xpath = False
            # Construct the actual selector string used for logging/metadata
            if selector_type_key == 'id':
                actual_selector_str = f"#{CSS.escape(selector_value)}"
                selenium_by = By.CSS_SELECTOR
            elif selector_type_key == 'class':
                actual_selector_str = f".{CSS.escape(selector_value.split()[0])}" 
                selenium_by = By.CSS_SELECTOR
            elif selector_type_key == 'xpath':
                actual_selector_str = selector_value
                selenium_by = By.XPATH
                is_xpath = True # Not used further, but for clarity
            else: # css
                actual_selector_str = selector_value
                selenium_by = By.CSS_SELECTOR
            
            full_selector_meta = f"{selector_type_key}={actual_selector_str}"
            selectors_tried.append(full_selector_meta)
            try:
                elements = search_context.find_elements(selenium_by, actual_selector_str)
                visible_elements = [el for el in elements if self._is_visible(el)]
                if visible_elements:
                    self.log.debug(f"_try_direct_selectors: Found element with {full_selector_meta}")
                    return visible_elements[0], full_selector_meta # Return element and the selector string used
            except Exception as e:
                self.log.debug(f"_try_direct_selectors: Selector {full_selector_meta} failed: {e}")
                continue
        self.log.debug(f"_try_direct_selectors: Failed to find element with any of these direct selectors: {selectors_tried}")
        return None
    
    def _try_smart_matching(self, search_context, params: Dict) -> Optional[Tuple[Any, str]]:
        """Smart matching. Returns (element, match_type_key) or None."""
        element_type_param = params.get('type', 'input') # HTML element type like 'input', 'button'
        
        # Order of preference for matching criteria
        match_criteria_keys = ['text', 'placeholder', 'aria_label', 'value', 'title']

        base_selectors_map = {
            'input': ["input[type='text']", "input[type='search']", "input[type='email']", "input:not([type])", "textarea"],
            'button': ["button", "input[type='submit']", "input[type='button']", "[role='button']"],
            'link': ["a[href]"],
            'image': ["img"],
            # Add more specific types if needed, or allow passing element_type_param directly as selector
        }
        base_css_selectors = base_selectors_map.get(element_type_param, [element_type_param]) # Default to using element_type_param as selector if not in map

        for attempt_key in match_criteria_keys:
            pattern_to_match = params.get(attempt_key)
            if not pattern_to_match: # If this specific param (e.g. 'text') is not provided in call, skip
                continue

            for base_css_sel in base_css_selectors:
                try:
                    elements = search_context.find_elements(By.CSS_SELECTOR, base_css_sel)
                    for element in elements:
                        if not self._is_visible(element):
                            continue
                        
                        match_found = False
                        if attempt_key == 'text' and self._text_matches(element, pattern_to_match):
                            match_found = True
                        elif attempt_key == 'value' and self._attr_matches(element, 'value', pattern_to_match):
                             match_found = True
                        elif attempt_key == 'placeholder' and self._attr_matches(element, 'placeholder', pattern_to_match):
                            match_found = True
                        elif attempt_key == 'aria_label' and self._attr_matches(element, 'aria-label', pattern_to_match):
                            match_found = True
                        elif attempt_key == 'title' and self._attr_matches(element, 'title', pattern_to_match):
                            match_found = True
                        # Add other attribute checks if necessary

                        if match_found:
                            self.log.debug(f"_try_smart_matching: Found by '{attempt_key}'='{pattern_to_match}' in a '{base_css_sel}'")
                            return element, attempt_key # Return element and the key used for matching
                except Exception as e:
                    self.log.debug(f"_try_smart_matching: Error for base selector '{base_css_sel}' with {attempt_key}: {e}")
                    continue
        self.log.debug(f"_try_smart_matching: Failed for params: {params}")
        return None
    
    def _try_content_analysis(self, driver, search_context, params: Dict) -> Optional[Tuple[Any, str]]:
        """Content-based analysis. Returns (element, constructed_selector_string) or None."""
        text_pattern = params.get('text')
        if not text_pattern:
            self.log.debug("_try_content_analysis: No text_pattern provided, skipping.")
            return None
        self.log.debug(f"_try_content_analysis: Searching for text pattern '{text_pattern}'")

        try:
            html_source = ""
            if hasattr(search_context, 'execute_script'):
                if search_context == driver:
                    html_source = driver.page_source
                else: 
                    html_source = search_context.execute_script("return this.innerHTML")
            else:
                 self.log.warning("_try_content_analysis: search_context is not a valid WebDriver or ShadowRoot.")
                 return None

            if not html_source:
                self.log.debug("Could not get HTML source for content analysis.")
                return None

            soup = BeautifulSoup(html_source, "html.parser")
            
            if text_pattern:
                compiled_pattern = re.compile(re.escape(text_pattern), re.I)
                matching_text_nodes = soup.find_all(string=compiled_pattern)
                self.log.debug(f"_try_content_analysis: Found {len(matching_text_nodes)} text nodes matching '{text_pattern}'.")
                
                for text_node in matching_text_nodes:
                    if not text_node.string or not text_node.string.strip():
                        continue
                    candidate_parents = []
                    current_parent = text_node.parent
                    depth = 0
                    while current_parent and current_parent.name not in ['body', 'html'] and depth < 7:
                        score = 0
                        parent_text_content = current_parent.get_text(strip=True)
                        if len(parent_text_content) < len(text_node.string.strip()) * 1.1 and not current_parent.attrs and current_parent.name not in ['li', 'a', 'button', 'td', 'th']:
                            current_parent = current_parent.parent
                            depth +=1
                            continue
                        tag_scores = {'article': 5, 'li': 5, 'tr': 5, 'section': 4, 'main': 4, 'ul': 3, 'ol': 3, 'table':3, 'form': 3, 'figure': 3, 'aside': 3, 'nav': 3, 'header':3, 'footer':3}
                        score += tag_scores.get(current_parent.name, 0)
                        if current_parent.name in ['div', 'p', 'td', 'span']: score += 1
                        aria_role = current_parent.get('role')
                        if aria_role:
                            role_scores = {
                                'listitem': 7, 'article': 7, 'row': 6, 'gridcell': 6, 'feed': 5, 'document': 5, 
                                'region': 5, 'log': 5, 'status': 5, 'tabpanel': 5, 'dialog': 4, 'alertdialog': 4,
                                'list': 4, 'grid': 4, 'rowgroup': 4, 'table': 4, 'tablist': 3, 'toolbar': 3, 'menubar': 3
                            }
                            score += role_scores.get(aria_role, 0)
                            if aria_role in ['presentation', 'none']: score -= 7
                        if len(current_parent.find_all(True, recursive=False)) > 1 : score += 3
                        if len(current_parent.find_all(True, recursive=False)) == 0 and len(parent_text_content) == len(text_node.string.strip()):
                             score -=2
                        has_id = False
                        for attr_name, attr_val in current_parent.attrs.items():
                            if attr_name.startswith('data-'): score += 2
                            if attr_name == 'id': score += 3; has_id = True
                            if attr_name == 'name': score += 2
                            if attr_name == 'href' and current_parent.name == 'a': score += 4
                            if attr_name == 'src' and current_parent.name == 'img': score += 3
                            if attr_name == 'class' and isinstance(attr_val, list) and any('item' in c.lower() or 'result' in c.lower() for c in attr_val): score += 3
                        if current_parent.name == 'div' and len(parent_text_content) > 0.6 * len(soup.get_text(strip=True)) and score < 8 and not has_id :
                            score -= 5
                        if text_node.string and text_node.string.strip() not in parent_text_content:
                            score = -1
                        if score >= 0:
                            candidate_parents.append({'element': current_parent, 'score': score, 'depth': depth, 'text_len': len(parent_text_content)})
                        current_parent = current_parent.parent
                        depth += 1
                    target_soup_element = None
                    if not candidate_parents:
                        if text_node.parent and text_node.parent.name not in ['body', 'html']:
                             target_soup_element = text_node.parent
                             self.log.debug(f"_try_content_analysis: No scored candidate parents found for text '{text_node.string[:50].strip()}...'. Using immediate parent '{target_soup_element.name}'.")
                        else:
                            self.log.debug(f"_try_content_analysis: No suitable parent found for text '{text_node.string[:50].strip()}...'. Skipping this text node.")
                            continue
                    else:
                        candidate_parents.sort(key=lambda x: (-x['score'], abs(x['text_len'] - 150), x['depth']))
                        best_candidate = candidate_parents[0]
                        target_soup_element = best_candidate['element']
                        self.log.debug(f"_try_content_analysis: Best candidate parent for text '{text_node.string[:50].strip()}...' is '{target_soup_element.name}' with score {best_candidate['score']}, depth {best_candidate['depth']}, text_len {best_candidate['text_len']}.")
                    if not target_soup_element:
                        self.log.debug(f"_try_content_analysis: target_soup_element is None even after fallbacks for text '{text_node.string[:50].strip()}...'. Skipping.")
                        continue

                    self.log.debug(f"_try_content_analysis: Trying to convert soup element '{target_soup_element.name}' to Selenium element for text '{text_node.string[:50].strip()}...'.")
                    selenium_conversion_result = self._soup_to_selenium(search_context, target_soup_element)
                    if selenium_conversion_result:
                        selenium_element, used_selector_str = selenium_conversion_result
                        if self._is_visible(selenium_element):
                            self.log.info(f"_try_content_analysis: Successfully converted and verified visible Selenium element from soup for text '{text_pattern}' using selector '{used_selector_str}'.")
                            return selenium_element, used_selector_str # Return element and selector string
                        else:
                             self.log.debug(f"_try_content_analysis: Converted element from soup (selector '{used_selector_str}') is not visible.")
                    else:
                        self.log.debug(f"_try_content_analysis: Failed to convert soup element to Selenium for text '{text_pattern}'. Soup: {target_soup_element.name}")
                            
        except Exception as e:
            self.log.debug(f"_try_content_analysis: Failed for text pattern '{text_pattern}': {e}", exc_info=True)
        self.log.debug(f"_try_content_analysis: Failed to find element for text pattern '{text_pattern}'.")
        return None
    
    def _soup_to_selenium(self, search_context, soup_element) -> Optional[Tuple[Any, str]]:
        """Convert BeautifulSoup element to Selenium element. Returns (element, selector_string) or None."""
        # Attempt 1: Use ID if present and hopefully unique
        soup_id = soup_element.get('id')
        if soup_id:
            try:
                id_selector_str = f"#{CSS.escape(soup_id)}"
                self.log.debug(f"_soup_to_selenium: Trying ID selector: {id_selector_str}")
                element = search_context.find_element(By.CSS_SELECTOR, id_selector_str)
                self.log.debug(f"_soup_to_selenium: Found element by ID: {id_selector_str}")
                return element, id_selector_str # Return element and selector string
            except NoSuchElementException:
                self.log.debug(f"_soup_to_selenium: ID '{soup_id}' not unique or found in context.")
            except Exception as e_id_sel:
                 self.log.debug(f"_soup_to_selenium: Error finding by ID '{soup_id}': {e_id_sel}")

        # Attempt 2: Construct a more specific selector using tag name and prioritized attributes
        try:
            tag_name = soup_element.name
            attrs = soup_element.attrs
            
            def _attr_sel_str(attr, val):
                escaped_val = val
                if not re.match(r"^[a-zA-Z0-9_\-]+$", val):
                    escaped_val = CSS.escape(val)
                return f'[{attr}="{escaped_val}"]'

            priority_attrs_map = {
                'data-testid': 10, 'data-cy': 10, 'data-qa': 10,
                'role': 8, 'name': 7, 'title': 5, 'aria-label': 5,
                'aria-labelledby': 5, 'aria-describedby': 4,
            }
            
            best_attr_css_selector = None
            highest_priority_score = 0

            for p_attr, score in priority_attrs_map.items():
                if p_attr in attrs:
                    value = attrs[p_attr]
                    if isinstance(value, list): value = ' '.join(value)
                    if value:
                        current_css_selector = tag_name + _attr_sel_str(p_attr, value)
                        try:
                            sel_element = search_context.find_element(By.CSS_SELECTOR, current_css_selector)
                            self.log.debug(f"_soup_to_selenium: Prioritized attribute selector '{current_css_selector}' is unique.")
                            return sel_element, current_css_selector # Return element and selector
                        except NoSuchElementException:
                            self.log.debug(f"_soup_to_selenium: Prioritized attribute selector '{current_css_selector}' not found or not unique.")
                        except Exception as e_test_sel:
                            self.log.debug(f"_soup_to_selenium: Error testing selector '{current_css_selector}': {e_test_sel}")
                        if score > highest_priority_score:
                            highest_priority_score = score
                            best_attr_css_selector = current_css_selector 
            
            if best_attr_css_selector and highest_priority_score > 0:
                 self.log.debug(f"_soup_to_selenium: Trying best high-priority attribute selector (unconfirmed uniqueness): {best_attr_css_selector}")
                 try:
                     sel_element = search_context.find_element(By.CSS_SELECTOR, best_attr_css_selector)
                     self.log.debug(f"_soup_to_selenium: Found element with best_attr_selector: {best_attr_css_selector}")
                     return sel_element, best_attr_css_selector # Return element and selector
                 except NoSuchElementException:
                     self.log.debug(f"_soup_to_selenium: Best_attr_selector {best_attr_css_selector} still not found.")
                 except Exception as e_best_attr_sel:
                     self.log.debug(f"_soup_to_selenium: Error with best_attr_selector '{best_attr_css_selector}': {e_best_attr_sel}")

            if 'class' in attrs and isinstance(attrs['class'], list):
                classes = attrs['class']
                stable_classes = [c for c in classes if re.match(r"^[a-zA-Z][a-zA-Z0-9_-]+$", c) and len(c) > 2 and len(c) < 30]
                stable_classes.sort(key=len)

                for cls in stable_classes:
                    class_css_selector = f"{tag_name}.{CSS.escape(cls)}"
                    try:
                        elements = search_context.find_elements(By.CSS_SELECTOR, class_css_selector)
                        if len(elements) == 1:
                            self.log.debug(f"_soup_to_selenium: Found unique element with tag.class selector: {class_css_selector}")
                            return elements[0], class_css_selector # Return element and selector
                        else:
                            self.log.debug(f"_soup_to_selenium: Tag.class selector '{class_css_selector}' yielded {len(elements)} elements.")
                    except Exception as e_cls_sel:
                        self.log.debug(f"_soup_to_selenium: Error testing tag.class selector '{class_css_selector}': {e_cls_sel}")
            
            self.log.debug(f"_soup_to_selenium: Could not construct a reliably unique CSS selector for <{tag_name} class='{attrs.get('class')}'> based on its attributes.")

        except Exception as e_construct_sel:
            self.log.debug(f"_soup_to_selenium: General error during CSS selector construction: {e_construct_sel}", exc_info=True)

        self.log.debug(f"_soup_to_selenium: Failed to convert soup element ({soup_element.name}) to a unique Selenium element using attribute-based CSS selectors.")
        return None
    
    def _is_visible(self, element) -> bool:
        """Check if element is visible and interactable"""
        try:
            return element.is_displayed() and element.is_enabled()
        except Exception:
            return False
    
    def _text_matches(self, element, pattern: str) -> bool:
        """Check if element text matches pattern"""
        try:
            element_text = element.text.lower()
            return pattern.lower() in element_text
        except Exception:
            return False
    
    def _attr_matches(self, element, attr: str, pattern: str) -> bool:
        """Check if element attribute matches pattern"""
        try:
            attr_value = element.get_attribute(attr) or ""
            return pattern.lower() in attr_value.lower()
        except Exception:
            return False
    
    def wait_for_element(self, driver, timeout: int = None, **search_params) -> Optional[Any]:
        """Wait for element to appear"""
        timeout = timeout or self.config.default_wait_timeout
        
        try:
            # Simple wait for basic selectors
            if 'css' in search_params:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, search_params['css']))
                )
                return element
            elif 'xpath' in search_params:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, search_params['xpath']))
                )
                return element
        except TimeoutException:
            pass
        
        # Fallback to adaptive finding with retries
        start_time = time.time()
        while time.time() - start_time < timeout:
            element = self.find_element(driver, **search_params)
            if element:
                return element
            time.sleep(0.5)
        
        return None
    
    def extract_content(self, 
                        driver_or_html_content: Union[uc.Chrome, str], 
                        selectors_config: Optional[Union[Dict[str, str], List[Dict[str, str]]]] = None,
                        content_type: str = 'text', # 'text', 'html', 'attributes', 'list', 'table', 'article', 'structured'
                        default_selector: Optional[str] = None, # Fallback selector if primary fails or not given
                        base_url: Optional[str] = None # For resolving relative URLs if HTML string is passed
                        ) -> Union[str, List[str], List[Dict[str, str]], Dict[str, Any], None]:
        """
        Versatile content extraction method.
        - If selectors_config is a dict: extracts a single piece of data.
        - If selectors_config is a list of dicts: extracts a list of items (like a list or table rows).
        - content_type determines what to extract: text, inner/outer HTML, specific attributes, or structured article content.
        - If selectors_config is None and content_type is 'article' or 'structured', uses heuristic-based extraction.
        """
        self.log.debug(f"Attempting to extract content with type: {content_type}, selectors: {selectors_config is not None}")

        if content_type in ['article', 'structured']:
            # For 'article' or 'structured', we always use the new heuristic-based method.
            # selectors_config might be used in the future to guide this, but for now, it's ignored.
            if selectors_config:
                self.log.debug(f"Selectors config provided for content_type '{content_type}', but it will be ignored. Using heuristic extraction.")
            return self.extract_article_content(driver_or_html_content, base_url=base_url)

        # --- Existing logic for other content types (text, html, attributes, list, table) ---
        if not selectors_config and not default_selector:
            self.log.error("Selectors config or a default selector must be provided for content_types other than 'article' or 'structured'.")
            return None
        
        html_content: Optional[str] = None

        if isinstance(driver_or_html_content, str):
            html_content = driver_or_html_content
        else: # Assumes uc.Chrome or compatible WebDriver
            try:
                html_content = driver_or_html_content.page_source
            except Exception as e:
                self.log.error(f"Failed to get page source from driver: {e}")
                return None

        if not html_content:
            self.log.error("HTML content is empty for extract_content.")
            return None

        if content_type == 'text':
            # Extract visible text
            soup = BeautifulSoup(html_content, "html.parser")
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            return soup.get_text(separator=' ', strip=True)
        elif content_type == 'html':
            # Extract full HTML content
            return html_content
        elif content_type == 'attributes':
            # Extract specific attributes
            if not selectors_config:
                self.log.error("Selectors config must be provided for content_type 'attributes'.")
                return None
            extracted_attributes = {}
            for selector in selectors_config:
                element = self.find_element(driver_or_html_content, css=selector)
                if element:
                    extracted_attributes[selector] = element.value.get_attribute(selector)
            return extracted_attributes
        elif content_type == 'list':
            # Extract a list of items
            if not selectors_config:
                self.log.error("Selectors config must be provided for content_type 'list'.")
                return None
            extracted_list = []
            for selector in selectors_config:
                elements = driver_or_html_content.find_elements(By.CSS_SELECTOR, selector)
                extracted_list.extend([el.value.get_attribute(selector) for el in elements if el.value])
            return extracted_list
        elif content_type == 'table':
            # Extract table rows
            if not selectors_config:
                self.log.error("Selectors config must be provided for content_type 'table'.")
                return None
            extracted_table = []
            for selector in selectors_config:
                rows = driver_or_html_content.find_elements(By.CSS_SELECTOR, selector)
                extracted_table.extend([el.value.get_attribute(selector) for el in rows if el.value])
            return extracted_table
        else:
            self.log.error(f"Unknown content_type: {content_type}")
            return None

    def find_input_field(self, driver, **hints) -> Optional[Any]:
        """Find input field with various hints"""
        # Try with hints first
        if hints:
            return self.find_element(driver, type='input', **hints)
        
        # Fallback to common input selectors
        selectors = [
            "input[type='text']",
            "input[type='search']", 
            "textarea",
            "input:not([type])"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                visible_elements = [el for el in elements if self._is_visible(el)]
                if visible_elements:
                    # Return the largest input field
                    return max(visible_elements, key=lambda e: e.size.get('width', 0) * e.size.get('height', 0))
            except Exception:
                continue
        
        return None
    
    def find_submit_button(self, driver, form_element=None) -> Optional[Any]:
        """Find submit button"""
        search_scope = form_element if form_element else driver
        
        # First try direct submit selectors
        selectors = [
            "input[type='submit']",
            "button[type='submit']"
        ]
        
        for selector in selectors:
            try:
                elements = search_scope.find_elements(By.CSS_SELECTOR, selector)
                visible_elements = [el for el in elements if self._is_visible(el)]
                if visible_elements:
                    return visible_elements[0]
            except Exception:
                continue
        
        # Then try buttons with common text
        button_texts = ['search', 'submit', 'go']
        
        for text in button_texts:
            try:
                xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]"
                elements = search_scope.find_elements(By.XPATH, xpath)
                visible_elements = [el for el in elements if self._is_visible(el)]
                if visible_elements:
                    return visible_elements[0]
            except Exception:
                continue
        
        return None
    
    def extract_item_details_from_list(
        self,
        driver,
        container_selector: Union[str, List[str]],
        item_detail_selectors: Dict[str, Dict[str, str]],
        max_items: Optional[int] = None
    ) -> List[Dict[str, ExtractedElement]]:
        """Extracts details from a list of items based on a container and detail selectors.
        Each item in the returned list is a dictionary where keys are detail names and
        values are ExtractedElement objects.
        The 'selector' for a detail in item_detail_selectors can be a string or a list of strings (fallback selectors).
        """
        extracted_items_list_of_dicts: List[Dict[str, ExtractedElement]] = []
        item_elements: List[Any] = [] # List of Selenium WebElements

        # Determine actual item elements to iterate over
        if isinstance(container_selector, str):
            self.log.debug(f"Attempting to extract items using single container selector: {container_selector}")
            try:
                item_elements = driver.find_elements(By.CSS_SELECTOR, container_selector)
            except Exception as e_find_single:
                self.log.error(f"Error finding item containers with selector '{container_selector}': {e_find_single}")
                return [] # Return empty list on error
        elif isinstance(container_selector, list):
            self.log.debug(f"Attempting to extract items using list of container selectors: {container_selector}")
            for i_sel, sel_str in enumerate(container_selector):
                try:
                    current_elements = driver.find_elements(By.CSS_SELECTOR, sel_str)
                    if current_elements:
                        self.log.info(f"Using container selector '{sel_str}' (attempt {i_sel+1}/{len(container_selector)}) - found {len(current_elements)} elements.")
                        item_elements = current_elements
                        break 
                    else:
                        self.log.debug(f"Container selector '{sel_str}' (attempt {i_sel+1}/{len(container_selector)}) yielded no elements.")
                except Exception as e_find_list_item:
                    self.log.warning(f"Error finding item containers with selector from list '{sel_str}' (attempt {i_sel+1}): {e_find_list_item}")
            if not item_elements:
                self.log.warning(f"None of the provided container selectors yielded results: {container_selector}")
                return []
        else:
            self.log.error(f"Invalid container_selector type: {type(container_selector)}. Must be a string or a list of strings.")
            return []

        self.log.debug(f"Found {len(item_elements)} potential item containers to process.")

        # Outer try-except for the loop over item_elements
        try: 
            for item_idx, item_elem_context in enumerate(item_elements):
                if max_items is not None and len(extracted_items_list_of_dicts) >= max_items:
                    break
                
                current_item_all_details: Dict[str, ExtractedElement] = {}
                all_required_found_for_item = True

                for detail_name, selector_info_dict in item_detail_selectors.items():
                    detail_css_selector_or_list = selector_info_dict['selector'] 
                    extract_type_full = selector_info_dict.get('type', 'text')
                    is_required = selector_info_dict.get('is_required', False)
                    
                    current_item_all_details[detail_name] = ExtractedElement(
                        name=detail_name, value=None, extraction_type=extract_type_full,
                        source_selector=str(detail_css_selector_or_list), properties=None, extraction_successful=False
                    )

                    selectors_to_attempt_for_detail: List[str] = []
                    if isinstance(detail_css_selector_or_list, str):
                        selectors_to_attempt_for_detail.append(detail_css_selector_or_list)
                    elif isinstance(detail_css_selector_or_list, list):
                        selectors_to_attempt_for_detail.extend(filter(None, detail_css_selector_or_list))
                    else:
                        self.log.warning(f"Invalid selector format for detail '{detail_name}': {detail_css_selector_or_list}. Skipping this detail for item {item_idx+1}.")
                        if is_required: 
                            all_required_found_for_item = False
                            self.log.debug(f"Required detail '{detail_name}' has invalid selector format, item {item_idx+1} will be incomplete.")
                        continue # to next detail_name

                    detail_extracted_successfully_this_item = False
                    for s_idx, individual_selector_str in enumerate(selectors_to_attempt_for_detail):
                        if not (individual_selector_str and isinstance(individual_selector_str, str)):
                            self.log.debug(f"Skipping invalid individual selector string ('{individual_selector_str}') for detail '{detail_name}' in item {item_idx+1}.")
                            continue
                        
                        # Inner try-except for finding/processing a single detail with one selector string
                        try:
                            detail_selenium_element = item_elem_context.find_element(By.CSS_SELECTOR, individual_selector_str)
                            
                            element_props = ElementProperties(
                                tag_name=detail_selenium_element.tag_name,
                                attributes={attr['name']: attr['value'] for attr in detail_selenium_element.get_property('attributes') if attr['name'] and attr['value']},
                                text=detail_selenium_element.text, 
                                is_displayed=detail_selenium_element.is_displayed(),
                                is_enabled=detail_selenium_element.is_enabled(),
                                location=detail_selenium_element.location,
                                size=detail_selenium_element.size,
                                raw_webelement=detail_selenium_element 
                            ) # Closed ElementProperties parenthesis
                            
                            extracted_value: Any = None
                            actual_extract_type = extract_type_full
                            attribute_name_for_extraction = None
                            if ':' in extract_type_full:
                                actual_extract_type, attribute_name_for_extraction = extract_type_full.split(':', 1)

                            if actual_extract_type == 'text':
                                extracted_value = detail_selenium_element.text.strip()
                            elif actual_extract_type == 'attribute' and attribute_name_for_extraction:
                                extracted_value = detail_selenium_element.get_attribute(attribute_name_for_extraction)
                            elif actual_extract_type == 'element':
                                extracted_value = detail_selenium_element 
                            else:
                                self.log.warning(f"Unknown extraction type '{extract_type_full}' for '{detail_name}' in item {item_idx+1}.")
                            
                            current_item_all_details[detail_name] = ExtractedElement(
                                name=detail_name, value=extracted_value, extraction_type=extract_type_full,
                                source_selector=individual_selector_str, properties=element_props, extraction_successful=True
                            )
                            self.log.debug(f"Successfully extracted detail '{detail_name}' for item {item_idx+1} using selector '{individual_selector_str}' (attempt {s_idx+1}/{len(selectors_to_attempt_for_detail)}).")
                            detail_extracted_successfully_this_item = True
                            break # Successfully extracted this detail with one of the selectors, move to next detail_name

                        except NoSuchElementException:
                            self.log.debug(f"Detail '{detail_name}' (selector: '{individual_selector_str}') not found in item {item_idx+1} (attempt {s_idx+1}/{len(selectors_to_attempt_for_detail)}).")
                        except StaleElementReferenceException:
                            self.log.warning(f"StaleElementReferenceException for detail '{detail_name}' (selector: '{individual_selector_str}') in item {item_idx+1}. Item might be changing during extraction.")
                            # This attempt for this selector fails; loop for selectors continues or is handled by is_required logic below.
                        except Exception as e_detail_extraction:
                            self.log.warning(f"Error extracting detail '{detail_name}' (selector: '{individual_selector_str}') from item {item_idx+1}: {e_detail_extraction}")
                        # End of inner try-except for individual_selector_str
                        
                    # After trying all selectors for a given detail_name:
                    if is_required and not detail_extracted_successfully_this_item:
                        all_required_found_for_item = False # Mark item as failing requirements
                        self.log.debug(f"Required detail '{detail_name}' failed to extract for item {item_idx+1} after all selector attempts. This item will be considered incomplete or skipped.")
                        break # Stop processing further details for THIS item if a required one failed completely
                # End of loop for detail_name
                
                # After processing all details for an item:
                if all_required_found_for_item:
                    # Add item if all required fields were found and at least one detail was successfully extracted
                    if any(de.extraction_successful for de in current_item_all_details.values()):
                        extracted_items_list_of_dicts.append(current_item_all_details)
                        title_ext_elem = current_item_all_details.get('title') 
                        log_title = title_ext_elem.value[:50] if title_ext_elem and title_ext_elem.extraction_successful and isinstance(title_ext_elem.value, str) else "[No Title]"
                        self.log.debug(f"Successfully processed and added item {item_idx+1}: {log_title}...")
                    else:
                        title_ext_elem = current_item_all_details.get('title') 
                        log_title = title_ext_elem.value[:50] if title_ext_elem and title_ext_elem.extraction_successful and isinstance(title_ext_elem.value, str) else "[No Title]"
                        self.log.debug(f"Item {item_idx+1} ({log_title}) had all required details present (or no details were required), but no actual data was extracted for any detail. Skipping.")
                else: # Some required detail was not found or failed to extract
                     title_ext_elem = current_item_all_details.get('title') 
                     log_title = title_ext_elem.value[:50] if title_ext_elem and title_ext_elem.extraction_successful and isinstance(title_ext_elem.value, str) else "[No Title]"
                     self.log.debug(f"Item {item_idx+1} ({log_title}) skipped due to missing/failed required details.")
            # End of loop for item_idx, item_elem_context

        except StaleElementReferenceException:
            self.log.warning("StaleElementReferenceException encountered while iterating through main item containers. List may be incomplete.")
        except Exception as e_general_item_loop:
            self.log.error(f"General error during the main loop for processing item containers: {e_general_item_loop}", exc_info=True)
        
        self.log.info(f"Extraction from list complete. Successfully processed and added {len(extracted_items_list_of_dicts)} items to results.")
        return extracted_items_list_of_dicts 

    def _find_main_content_scope(self, soup: BeautifulSoup, driver: Optional[Any] = None) -> Tuple[BeautifulSoup, str]:
        """
        Identifies the main content area of a page using a chain of heuristics.
        Returns a tuple of (BeautifulSoup_scope, strategy_used_description_string).
        If driver is provided, can be used for visibility checks if needed (not currently).
        """
        # More specific classes first, then more generic ones.
        # Common IDs that often denote the primary content container.
        # Semantic tags <main> and <article> are high priority.
        # ARIA role="main" is also a strong indicator.

        strategies_tried: List[Tuple[str, Union[str, List[str]]]] = [
            ("tag", "article"), # High semantic importance
            ("tag", "main"),
            ("role", "main"),
            ("id", ["article", "story", "entry-content", "post-content", "article-body", "main-content", "maincontent", "content"]), # Ordered by assumed specificity
            # Added more specific common article class names at the beginning
            ("class", ["article__body", "article-content", "article-text", "story-body", "entry-content", "post-content", "post__content", "text-content", "content__body", "article-body", "article__content", "main-story", "story-detail", "storytext", "articletext", "field-name-body", "page-content", "article-content-wrapper", "td-post-content", "hentry", "main-content", "content-main", "content", "main"]) 
        ]

        # Negative keywords that might indicate a non-primary content area if a generic selector matches
        negative_keywords = ["menu", "nav", "sidebar", "trending", "related", "footer", "header", "comments", "author-bio", "pagination", "tools", "share", "ad-", "promo", "slider", "carousel", "banner", "popup", "modal", "dialog"]

        self.log.debug("Attempting to find main content scope...")

        for strategy_type, selectors in strategies_tried:
            if isinstance(selectors, str): # Single selector string
                selector_list = [selectors]
            else: # List of selectors
                selector_list = selectors

            for selector_value in selector_list:
                found_element = None
                description = f"{strategy_type}:{selector_value}"
                self.log.debug(f"  Trying strategy: {description}")
                current_elements_found = []

                if strategy_type == "tag":
                    current_elements_found = soup.find_all(selector_value)
                elif strategy_type == "role":
                    current_elements_found = soup.find_all(attrs={"role": selector_value})
                elif strategy_type == "id":
                    el_by_id = soup.find(id=selector_value)
                    if el_by_id: current_elements_found = [el_by_id]
                elif strategy_type == "class":
                    current_elements_found = soup.find_all(class_=re.compile(r'\b' + re.escape(selector_value) + r'\b'))
                
                # Process found elements for this selector_value before moving to the next selector_value
                for el_candidate in current_elements_found:
                    if not el_candidate: continue

                    # Negative keyword check: If a generic selector found this, does it look like a non-content block?
                    is_generic_selector = (strategy_type == "class" and selector_value in ["content", "main"]) or \
                                          (strategy_type == "id" and selector_value in ["content", "main", "main-content", "maincontent"])
                    
                    if is_generic_selector:
                        class_string = ' '.join(el_candidate.get('class', [])).lower()
                        id_string = el_candidate.get('id', '').lower()
                        combined_attrs = class_string + ' ' + id_string
                        
                        # Check for negative keywords
                        matched_negative_keyword = None
                        for neg_keyword in negative_keywords:
                            if neg_keyword in combined_attrs:
                                matched_negative_keyword = neg_keyword
                                break
                        
                        if matched_negative_keyword:
                            self.log.debug(f"  Strategy {description} for element <{el_candidate.name} class='{class_string}' id='{id_string}'> matched generic selector_value '{selector_value}'. It contains negative keyword '{matched_negative_keyword}' in combined_attrs '{combined_attrs}'. Skipping this candidate.")
                            continue # Skip this specific el_candidate, try next one
                        
                        # Additional check for generic selectors: must contain a headline (h1 or h2)
                        if not el_candidate.find(['h1', 'h2']):
                            self.log.debug(f"  Strategy {description} for element <{el_candidate.name} class='{class_string}' id='{id_string}'> matched generic selector_value '{selector_value}', passed negative keywords, but lacks H1/H2. Skipping.")
                            continue

                    # Basic validation: check text length
                    text_content = el_candidate.get_text(strip=True)
                    if len(text_content) > self.config.min_main_content_text_length: 
                        self.log.info(f"Main content scope identified using {description}. Text length: {len(text_content)}")
                        return el_candidate, description # Return the first valid candidate found
                    else:
                        self.log.debug(f"  Strategy {description} found an element, but it has too little text ({len(text_content)} chars). Trying next candidate or selector.")
        
        self.log.warning("Could not identify a specific main content area using heuristics. Falling back to <body>.")
        return soup.body if soup.body else soup, "fallback:body" 

    def extract_article_content(self, driver_or_html_content: Union[uc.Chrome, str], base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts structured content (title, headings, paragraphs, lists, links)
        from the main content area of a webpage.
        """
        html_content: str
        page_title_from_tag: str = ""
        current_url: Optional[str] = base_url

        if isinstance(driver_or_html_content, str):
            html_content = driver_or_html_content
            if not current_url:
                self.log.warning("base_url not provided with HTML string input for extract_article_content. Relative links might not resolve correctly.")
        else: # Assumes uc.Chrome or compatible WebDriver
            try:
                html_content = driver_or_html_content.page_source
                if not current_url:
                    current_url = driver_or_html_content.current_url
                page_title_from_tag = driver_or_html_content.title
            except Exception as e:
                self.log.error(f"Failed to get page source or URL from driver: {e}")
                return {
                    "url": current_url,
                    "page_title": "",
                    "article_title": "",
                    "error": f"Failed to access driver: {e}",
                    "headings": [], "paragraphs": [], "lists": [], "links": [],
                    "main_content_html": "", "detected_content_scope_selector": "error_before_parse"
                }

        if not html_content:
            self.log.error("HTML content is empty for extract_article_content.")
            return {
                "url": current_url,
                "page_title": "",
                "article_title": "",
                "error": "Empty HTML content",
                "headings": [], "paragraphs": [], "lists": [], "links": [],
                "main_content_html": "", "detected_content_scope_selector": "empty_html"
            }

        soup = BeautifulSoup(html_content, 'lxml')
        if not page_title_from_tag: # If not obtained from driver, try to get from soup
            title_tag = soup.find('title')
            if title_tag:
                page_title_from_tag = title_tag.get_text(strip=True)

        content_scope_soup, detected_scope_selector = self._find_main_content_scope(soup)

        article_title = ""
        headings_data = []
        paragraphs_data = []
        lists_data = []
        links_data = []
        main_content_html_str = str(content_scope_soup) if content_scope_soup else ""

        if content_scope_soup:
            # Article Title (prefer H1 within scope)
            h1_in_scope = content_scope_soup.find('h1')
            if h1_in_scope:
                article_title = h1_in_scope.get_text(separator=' ', strip=True)
            elif page_title_from_tag and detected_scope_selector == "fallback:body":
                # If we fell back to body, the page title might be the best article title
                article_title = page_title_from_tag
            
            # Headings
            for i in range(1, 7):
                for h_tag in content_scope_soup.find_all(f'h{i}'):
                    text = h_tag.get_text(separator=' ', strip=True)
                    if text:
                        headings_data.append({"level": i, "text": text})
            
            # Paragraphs
            for p_tag in content_scope_soup.find_all('p'):
                text = p_tag.get_text(separator='\n', strip=True) # Preserve line breaks within paragraph if meaningful
                if text:
                    paragraphs_data.append(text)
            
            # Lists (ul and ol)
            for list_tag in content_scope_soup.find_all(['ul', 'ol']):
                items = []
                for li_tag in list_tag.find_all('li', recursive=False): # Only direct children
                    item_text = li_tag.get_text(separator=' ', strip=True)
                    if item_text:
                        items.append(item_text)
                if items:
                    lists_data.append(items)
            
            # Links
            for a_tag in content_scope_soup.find_all('a', href=True):
                href = a_tag['href']
                text = a_tag.get_text(separator=' ', strip=True)
                if not text: # Try to get title or aria-label if text is empty (e.g. image link)
                    text = a_tag.get('title', a_tag.get('aria-label', '')).strip()
                if not text:
                    # Fallback for links with no discernible text (e.g. just an icon inside)
                    # Could use a placeholder like "[link]" or try to describe inner content if complex
                    img_alt = a_tag.find('img', alt=True)
                    if img_alt:
                        text = img_alt['alt']
                    else:
                        text = href # Last resort, use href itself if no text
                
                absolute_url = ""
                if current_url:
                    try:
                        absolute_url = urljoin(current_url, href)
                    except Exception as e_urljoin:
                        self.log.debug(f"Could not form absolute URL for {href} with base {current_url}: {e_urljoin}")
                        absolute_url = href # Fallback to original href
                
                links_data.append({"text": text, "href": absolute_url})
        else:
            self.log.warning("Content scope soup was None, cannot extract structured data.")

        return {
            "url": current_url,
            "page_title": page_title_from_tag,
            "article_title": article_title,
            "headings": headings_data,
            "paragraphs": paragraphs_data,
            "lists": lists_data,
            "links": links_data,
            "main_content_html": main_content_html_str,
            "detected_content_scope_selector": detected_scope_selector
        } 