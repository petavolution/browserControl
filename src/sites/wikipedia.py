"""
This module handles interactions with Wikipedia, including searching,
fetching page content, and downloading images.
It is structured as a Site Module for BrowserControL01.
"""

import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import os
from PIL import Image
import io
from pathlib import Path
import datetime # Added import for datetime

# Selenium imports - these are less critical if we use self.dom and self.behavior from BaseSiteModule
# However, some direct driver usage might remain for navigation or page_source.
# from selenium import webdriver # Not directly instantiating
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

from typing import Optional, Any, Dict, List, Tuple

# Project-specific imports
from .base_site import BaseSiteModule, site_registry
from core.config import SystemConfig, SiteConfig # For type hints
from utils.logger import StealthLogger # For logger type hint
import undetected_chromedriver as uc # For driver type hint
from utils.file_utils import ensure_directory_exists # For creating output dirs

# Helper: Selenium-based navigation and interaction (can be moved to utils later if generic enough)
# These were previously global, now can be static or instance methods if needed by the module.
# For now, let's make them static or integrate their logic directly.

def _navigate_wikipedia_search(driver: uc.Chrome, query_or_url: str, logger: Optional[StealthLogger] = None):
    """Navigates to the Wikipedia search/page URL."""
    if urlparse(query_or_url).scheme in ["http", "https"]:
        target_url = query_or_url
    else:
        # Default to English Wikipedia search
        target_url = f"https://en.wikipedia.org/w/index.php?search={query_or_url}"
    
    log_func = logger.info if logger else print
    log_func(f"Navigating to Wikipedia URL: {target_url}")
    try:
        driver.get(target_url)
        # Basic wait for title to ensure page starts loading. More specific waits can be added.
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        log_func(f"Successfully navigated to: {driver.current_url}")
        return True
    except TimeoutException:
        log_func = logger.error if logger else print
        log_func(f"Timeout navigating to {target_url}")
        return False
    except Exception as e:
        log_func = logger.error if logger else print
        log_func(f"Error navigating to {target_url}: {e}")
        return False

class WikipediaSiteModule(BaseSiteModule):
    """Site module for Wikipedia interactions."""

    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: StealthLogger, site_config: SiteConfig, **kwargs):
        super().__init__(driver=driver, config=config, logger=logger, site_config=site_config, **kwargs)
        self.driver = driver
        # self.config is SystemConfig from super
        # self.log is StealthLogger from super
        # self.site_config is SiteConfig from super
        self.log.info(f"WikipediaSiteModule initialized with managed WebDriver. Site: {self.site_config.name}")

    def validate_params(self, **params) -> bool:
        """Validate parameters for Wikipedia operations.

        Accepts 'query', 'query_or_url', or any of the standard aliases
        (q, url, search, term) which get normalized by the base class.
        """
        # After normalization by base class, we expect 'query' or 'query_or_url'
        normalized = self._normalize_params(params)
        if 'query' not in normalized and 'query_or_url' not in normalized:
            self.log.error("A query parameter is required for Wikipedia module (use 'query', 'q', 'url', etc.)")
            return False
        return True

    def search(self, query: str, **params) -> Dict[str, Any]:
        """Fulfills the abstract search method by calling get_data."""
        self.log.info(f"WikipediaModule 'search' called, redirecting to 'get_data' with query: {query}")
        # Map parameters as needed. 'query' becomes 'query_or_url'.
        # Other params from **params can be passed along if get_data accepts them.
        
        # Extract relevant parameters for get_data from **params or set defaults
        extract_text = params.get('extract_text', True)
        download_images_wider_than = params.get('download_images_wider_than', 640)
        output_subfolder_name = params.get('output_subfolder_name', None)

        return self.get_data(
            query_or_url=query, 
            extract_text=extract_text,
            download_images_wider_than=download_images_wider_than,
            output_subfolder_name=output_subfolder_name,
            **params # Pass along any other params that get_data might use
        )

    def get_data(self, 
                 query_or_url: str, 
                 extract_text: bool = True, 
                 download_images_wider_than: Optional[int] = 640, 
                 output_subfolder_name: Optional[str] = None,
                 exploration_depth: int = 0, # New parameter
                 max_pages_to_explore: int = 1, # New parameter
                 keywords_to_follow: Optional[List[str]] = None, # New parameter
                 _visited_urls: Optional[set] = None, # Internal for recursion
                 _current_pages_count: Optional[int] = 0, # DEPRECATED, will use len(_visited_urls)
                 _base_run_output_dir: Optional[Path] = None # New internal param for root output path of the run
                 ) -> Dict[str, Any]:
        """
        Main interaction method for Wikipedia.
        Searches Wikipedia, extracts text, downloads images, and can recursively explore links.
        Manages its own output directory under a main 'wikipedia_runs' directory.
        """
        
        if _visited_urls is None:
            _visited_urls = set() # Initialize for the first call

        # Check if URL is already processed or currently being processed higher in the call stack
        if query_or_url in _visited_urls:
             self.log.info(f"URL {query_or_url} already visited or in current processing chain. Skipping.")
             return self._create_success_result(data={'url': query_or_url, 'status': 'skipped_already_visited_or_processing'}, message="URL already visited/processing.")

        # Check against max_pages_to_explore using the size of the shared _visited_urls set
        if len(_visited_urls) >= max_pages_to_explore:
            self.log.info(f"Max pages to explore ({max_pages_to_explore}) reached based on visited set size ({len(_visited_urls)}). Skipping {query_or_url}.")
            return self._create_success_result(data={'url': query_or_url, 'status': 'skipped_max_pages_global'}, message="Max pages limit reached for the run.")

        _visited_urls.add(query_or_url) # Add current URL to mark it as being processed in this call
        current_processing_count = len(_visited_urls) # This is now the Nth page being processed in the run

        self.log.info(f"Wikipedia 'get_data' started. Query/URL: '{query_or_url}', Depth: {exploration_depth}, Processing page #{current_processing_count}/{max_pages_to_explore}")

        if not self.driver or not self.is_driver_active_from_module():
            return self._create_error_result(error_message="Browser driver is not active or available")

        if not _navigate_wikipedia_search(self.driver, query_or_url, self.log):
            return self._create_error_result(error_message=f"Failed to navigate to Wikipedia for: {query_or_url}", current_url=self.driver.current_url if self.driver else None)
        
        self.wait_for_page_ready(self.driver)
        
        page_url = self.driver.current_url # Actual URL after navigation/redirects
        # If the navigated URL is different from query_or_url (e.g., search term resolved to a page), add it to visited.
        if page_url != query_or_url and page_url in _visited_urls:
            self.log.info(f"Redirected to an already visited URL: {page_url}. Skipping.")
            return self._create_success_result(data={'url': page_url, 'status': 'skipped_visited_redirect'}, message="Redirected to URL already visited.")
        _visited_urls.add(page_url)


        html_content = self.driver.page_source
        page_title = self.driver.title
        sanitized_page_title_for_folder = re.sub(r'[^a-zA-Z0-9_\\-]', '_', page_title)[:100] if page_title else "untitled_page"

        parsed_data_content: Optional[Dict[str, Dict[str, Any]]] = None
        if extract_text:
            self.log.info(f"Parsing text content and links from {page_url}...")
            parsed_data_content = self._parse_page_content(html_content, base_url=page_url)

        image_paths = []
        output_path_str: Optional[str] = None
        # unique_run_id_for_page = "" # No longer needed in this form

        # Determine the base output directory for the entire run (initial call)
        # and the specific output directory for the current page.
        current_page_specific_output_dir: Optional[Path] = None

        if _base_run_output_dir is None: # This is the initial call in an exploration chain
            if hasattr(self.config, 'output_dir') and self.config.output_dir:
                main_output_dir_root = Path(self.config.output_dir)
            else:
                main_output_dir_root = self.config.base_path / "output"
            
            wiki_runs_dir = main_output_dir_root / "wikipedia_runs"

            if output_subfolder_name: # User specified a name for the run
                base_run_output_dir_for_this_run = wiki_runs_dir / output_subfolder_name
            else: # Generate a unique name for the run based on initial query and timestamp
                initial_query_base = re.sub(r'[^a-zA-Z0-9_\\-]', '_', query_or_url.split('/')[-1] if '/' in query_or_url else query_or_url)
                initial_query_timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                base_run_output_dir_for_this_run = wiki_runs_dir / f"{initial_query_base}_{initial_query_timestamp}"
            
            _resolved_base_run_output_dir = base_run_output_dir_for_this_run
        else: # This is a recursive call, use the passed-in base directory
            _resolved_base_run_output_dir = _base_run_output_dir

        # Now, create the specific folder for *this* page's content, inside the base run output dir
        if download_images_wider_than is not None and download_images_wider_than > 0 or parsed_data_content:
            # Use sanitized page title for the subfolder name to make it human-readable
            # Add a unique suffix in case of title collisions (though unlikely for different Wikipedia pages)
            page_folder_name = f"{sanitized_page_title_for_folder}_{datetime.datetime.now().strftime('%H%M%S_%f')}"
            current_page_specific_output_dir = _resolved_base_run_output_dir / page_folder_name
            
            ensure_directory_exists(current_page_specific_output_dir)
            output_path_str = str(current_page_specific_output_dir)

            if download_images_wider_than is not None and download_images_wider_than > 0:
                image_download_folder = current_page_specific_output_dir / "images"
                ensure_directory_exists(image_download_folder)
                self.log.info(f"Downloading images > {download_images_wider_than}px from {page_url} to {image_download_folder}")
                image_paths = self._download_images(html_content, page_url, str(image_download_folder), download_images_wider_than, self.log)
                self.log.info(f"Downloaded {len(image_paths)} images meeting criteria.")

            if parsed_data_content:
                text_content_file = current_page_specific_output_dir / "text_content.json"
                try:
                    with open(text_content_file, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(parsed_data_content, f, ensure_ascii=False, indent=4)
                    self.log.info(f"Text content and links saved to {text_content_file}")
                except Exception as e_json:
                    self.log.error(f"Failed to save text content to {text_content_file}: {e_json}")
        
        if parsed_data_content:
            self.log.info(f"Successfully parsed {len(parsed_data_content)} sections for {page_url}.")
        elif extract_text:
            self.log.warning(f"Text extraction enabled, but no structured content was parsed from {page_url}.")

        explored_pages_data = []
        if exploration_depth > 0 and parsed_data_content and len(_visited_urls) < max_pages_to_explore:
            self.log.info(f"Starting exploration from {page_url} (depth {exploration_depth}, keywords: {keywords_to_follow})")
            links_to_explore_on_this_page = [] # Use a temporary list for current page's candidates
            if keywords_to_follow:
                normalized_keywords = [kw.lower() for kw in keywords_to_follow]
                for section_title, section_content in parsed_data_content.items():
                    for link_info in section_content.get('links', []):
                        link_text_lower = link_info.get('text', '').lower()
                        if any(kw in link_text_lower for kw in normalized_keywords):
                            link_href = link_info.get('href')
                            # Crucial check: only consider if not ALREADY in the global _visited_urls
                            # and is a valid Wikipedia link, and not already queued from THIS page.
                            if link_href and link_href not in _visited_urls and urlparse(link_href).netloc.endswith('wikipedia.org') and link_href not in links_to_explore_on_this_page:
                                links_to_explore_on_this_page.append(link_href)
            
            self.log.debug(f"Found {len(links_to_explore_on_this_page)} unique, unvisited links on this page matching keywords for further exploration.")

            for i, link_to_visit in enumerate(links_to_explore_on_this_page):
                # Max pages check again before diving deeper, using the up-to-date len(_visited_urls)
                if len(_visited_urls) >= max_pages_to_explore:
                    self.log.info(f"Max pages ({max_pages_to_explore}) reached before exploring {link_to_visit}. Stopping further exploration from this page.")
                    break
                
                self.log.info(f"Exploring link {i+1}/{len(links_to_explore_on_this_page)}: {link_to_visit} (Depth remaining: {exploration_depth-1})")
                sub_page_data = self.get_data(
                    query_or_url=link_to_visit,
                    extract_text=extract_text,
                    download_images_wider_than=download_images_wider_than,
                    output_subfolder_name=None, # Not used by recursive calls for their own base, _base_run_output_dir is used
                    exploration_depth=exploration_depth - 1,
                    max_pages_to_explore=max_pages_to_explore,
                    keywords_to_follow=keywords_to_follow,
                    _visited_urls=_visited_urls, 
                    _current_pages_count=None, # Deprecated
                    _base_run_output_dir=_resolved_base_run_output_dir # Pass down the root output dir for the run
                )
                explored_pages_data.append(sub_page_data)
                # No need to manually update count here, len(_visited_urls) is the source of truth.

        return self._create_success_result(data={
            'url': page_url,
            'title': page_title,
            'parsed_content': parsed_data_content,
            'downloaded_images': image_paths,
            'output_path': output_path_str,
            'explored_pages': explored_pages_data,
            'exploration_summary': {
                'current_page_url': page_url, # Added for clarity in recursive calls
                'exploration_depth_for_this_page': exploration_depth,
                'pages_explored_from_this_page': len(explored_pages_data),
                'total_unique_urls_processed_in_run': len(_visited_urls)
            }
        })

    def _parse_page_content(self, html_content: str, base_url: str) -> Dict[str, Dict[str, Any]]:
        if not html_content:
            return {}

        soup = BeautifulSoup(html_content, 'lxml')
        main_content_container = soup.find(id='mw-content-text')
        if not main_content_container:
            self.log.warning("Could not find 'mw-content-text' div in Wikipedia page for parsing.")
            return {}

        # Try to find the more specific mw-parser-output div
        parser_output_div = main_content_container.find('div', class_='mw-parser-output')
        content_div_to_scan = parser_output_div if parser_output_div else main_content_container
        if parser_output_div:
            self.log.debug("Found 'mw-parser-output' div, using it as the primary content container.")
        else:
            self.log.debug("'mw-parser-output' not found, using 'mw-content-text' as content container.")

        toc = soup.find(id='toc') # TOC is usually outside mw-parser-output, so find from main soup
        sections: Dict[str, Dict[str, Any]] = {}
        current_section_title = "Introduction" 
        current_section_elements: List[Any] = [] # Store elements (p, lists, etc.) to process for text and links

        for element in content_div_to_scan.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'dl'], recursive=False):
            if element.name.startswith('h'):
                headline_span = element.find(class_='mw-headline')
                if headline_span:
                    if current_section_elements:
                        text_parts, links = self._extract_text_and_links_from_elements(current_section_elements, base_url)
                        sections[current_section_title] = {'text': '\n'.join(text_parts).strip(), 'links': links}
                    current_section_elements = []
                    current_section_title = headline_span.get_text(strip=True)
            elif element.name in ['p', 'ul', 'ol', 'dl']:
                current_section_elements.append(element)

        if current_section_elements: # Add the last collected section
            text_parts, links = self._extract_text_and_links_from_elements(current_section_elements, base_url)
            sections[current_section_title] = {'text': '\n'.join(text_parts).strip(), 'links': links}

        if toc:
            self.log.debug("TOC found, refining sections based on TOC structure.")
            structured_sections: Dict[str, Dict[str, Any]] = {}
            toc_links = toc.find_all('a', href=re.compile("^#"))
            
            toc_headlines = []
            for link_tag in toc_links:
                toc_text_span = link_tag.find('span', class_='toctext')
                if toc_text_span:
                    toc_headlines.append(toc_text_span.get_text(strip=True))

            intro_data = sections.get("Introduction")
            if intro_data and intro_data.get('text'): # Preserve intro content
                structured_sections["Introduction"] = intro_data
            
            for toc_title in toc_headlines:
                heading_element = content_div_to_scan.find(lambda tag: tag.name.startswith('h') and \
                                                   tag.find(class_='mw-headline') and \
                                                   tag.find(class_='mw-headline').get_text(strip=True) == toc_title)
                if heading_element:
                    section_elements_for_toc_item: List[Any] = []
                    for sibling in heading_element.find_next_siblings():
                        if sibling.name.startswith('h'):
                            sibling_headline_span = sibling.find(class_='mw-headline')
                            if sibling_headline_span and sibling_headline_span.get_text(strip=True) in toc_headlines:
                                break 
                        if sibling.name in ['p', 'ul', 'ol', 'dl']: # Collect relevant content elements
                            section_elements_for_toc_item.append(sibling)
                    
                    if section_elements_for_toc_item:
                        text_parts, links = self._extract_text_and_links_from_elements(section_elements_for_toc_item, base_url)
                        section_text_content = '\n'.join(text_parts).strip()
                        if section_text_content or links: # Only add section if it has text or links
                            structured_sections[toc_title] = {'text': section_text_content, 'links': links}
                else:
                    self.log.debug(f"TOC title '{toc_title}' not found as a heading in content. Skipping.")
            
            if not structured_sections and intro_data and not toc_headlines:
                 self.log.debug("TOC was present but no items parsed from it, or no matching content headings. Falling back to initial sections.")
                 return sections 
            elif not structured_sections and not intro_data:
                 self.log.warning("TOC parsing did not yield any structured sections, and no introduction found. Page might be structured differently.")
                 return sections 

            return structured_sections
        
        self.log.debug("No TOC found or TOC-based refinement not applied. Returning sections from direct heading scan.")
        return sections

    def _extract_text_and_links_from_elements(self, elements: List[Any], base_url: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """Helper to extract text and internal Wikipedia links from a list of BeautifulSoup elements."""
        text_parts: List[str] = []
        links: List[Dict[str, str]] = []
        
        for element in elements:
            # Get text from the element itself, handling lists appropriately
            if element.name in ['ul', 'ol', 'dl']:
                list_items_texts = []
                for li in element.find_all('li', recursive=False): # direct children list items
                    list_items_texts.append(f"  - {li.get_text(separator=' ', strip=True)}")
                text_parts.append('\n'.join(list_items_texts))
            else: # Typically 'p'
                text_parts.append(element.get_text(separator=' ', strip=True))

            # Find all links within this element
            for link_tag in element.find_all('a', href=True):
                href = link_tag['href']
                # Filter for internal Wikipedia links (relative, or full /wiki/ or /w/index.php links)
                if href.startswith('/wiki/') or href.startswith('./') or href.startswith('#') or \
                   (href.startswith('/') and not href.startswith('//') and 'index.php' in href) or \
                   (urlparse(href).netloc == urlparse(base_url).netloc and ('/wiki/' in href or 'index.php' in href)):
                    
                    link_text = link_tag.get_text(strip=True)
                    full_href = urljoin(base_url, href) # Ensure full URL

                    # Avoid duplicates and very short/non-descriptive link texts
                    if link_text and len(link_text) > 1 and not any(l['href'] == full_href for l in links):
                        parsed_href = urlparse(full_href)
                        # Further filter out non-article links like Special pages, File pages, etc. if desired
                        if not (parsed_href.path.startswith('/wiki/Special:') or \
                                parsed_href.path.startswith('/wiki/File:') or \
                                parsed_href.path.startswith('/wiki/Category:') or \
                                parsed_href.path.startswith('/wiki/Help:') or \
                                parsed_href.path.startswith('/wiki/Template:') or \
                                parsed_href.path.startswith('/wiki/Portal:') or \
                                parsed_href.path.startswith('/wiki/Wikipedia:')):
                             links.append({'text': link_text, 'href': full_href})
        return text_parts, links

    def _download_images(self, html_content: str, base_url: str, download_folder: str, min_width: int, logger: StealthLogger) -> List[str]:
        downloaded_image_paths = []
        if not html_content:
            return downloaded_image_paths

        soup = BeautifulSoup(html_content, 'lxml')
        # ensure_directory_exists is called by the caller `get_data`

        for img_tag in soup.find_all('img'):
            img_url = img_tag.get('src')
            if not img_url:
                continue

            img_url = urljoin(base_url, img_url) # Resolve relative URLs

            if img_url.startswith('data:') or img_url.endswith('.svg'): # Skip data URIs and SVGs
                logger.debug(f"Skipping decorative/SVG image: {img_url[:70]}...")
                continue
            
            if img_url.startswith('//'): # Protocol relative URLs
                parsed_base_url = urlparse(base_url)
                img_url = f"{parsed_base_url.scheme}:{img_url}"

            try:
                # Initial check for width attribute (often a thumbnail)
                attr_width = img_tag.get('width')
                if attr_width and attr_width.isdigit() and int(attr_width) < min_width:
                    logger.debug(f"Skipping image based on width attribute < {min_width}: {img_url}")
                    continue

                # Try to get the original image URL if it's a thumbnail (common in <figure>)
                parent_figure = img_tag.find_parent('figure')
                original_img_url = img_url # Start with current img_url
                
                if parent_figure:
                    link_to_file_page = parent_figure.find('a', class_='mw-file-description')
                    if link_to_file_page and link_to_file_page.get('href'):
                        file_page_url = urljoin(base_url, link_to_file_page.get('href'))
                        logger.debug(f"Found figure, attempting to get original from file page: {file_page_url}")
                        
                        # Fetching file page content - this is an external HTTP call
                        try:
                            file_page_response = httpx.get(file_page_url, follow_redirects=True, timeout=10.0)
                            file_page_response.raise_for_status()
                            file_soup = BeautifulSoup(file_page_response.text, 'lxml')
                            
                            # Find the link to the actual media file on the file page
                            media_link_div = file_soup.find('div', id='file') # Standard location for direct file link
                            if media_link_div:
                                direct_media_link_tag = media_link_div.find('a')
                                if direct_media_link_tag and direct_media_link_tag.get('href'):
                                    potential_original_url = urljoin(base_url, direct_media_link_tag.get('href'))
                                    if potential_original_url.startswith('//'):
                                        parsed_base_url = urlparse(base_url) # Re-parse if base_url was different for file page
                                        potential_original_url = f"{parsed_base_url.scheme}:{potential_original_url}"
                                    original_img_url = potential_original_url
                                    logger.debug(f"Got original image URL from file page's direct media link: {original_img_url}")
                            else: # Fallback if 'div#file' not found
                                full_image_div = file_soup.find('div', class_='fullImageLink') # Older structure
                                if full_image_div:
                                    full_image_link_tag = full_image_div.find('a')
                                    if full_image_link_tag and full_image_link_tag.get('href'):
                                        potential_original_url = urljoin(base_url, full_image_link_tag.get('href'))
                                        if potential_original_url.startswith('//'):
                                            parsed_base_url = urlparse(base_url)
                                            potential_original_url = f"{parsed_base_url.scheme}:{potential_original_url}"
                                        original_img_url = potential_original_url
                                        logger.debug(f"Got original image URL from file page's fullImageLink: {original_img_url}")
                        except httpx.RequestError as e_filepage:
                            logger.warning(f"HTTP error fetching file page {file_page_url}: {e_filepage}")
                        except Exception as e_file_parse:
                            logger.warning(f"Error parsing file page {file_page_url}: {e_file_parse}")

                # Download the (potentially original) image data
                img_response = httpx.get(original_img_url, timeout=20.0) # Increased timeout for larger images
                img_response.raise_for_status()
                img_data = img_response.content

                # Check actual dimensions with Pillow
                image_for_pillow = io.BytesIO(img_data)
                img = Image.open(image_for_pillow)
                
                if img.width >= min_width:
                    logger.info(f"Image {original_img_url} ({img.width}x{img.height}) meets size criteria (>= {min_width}px width). Downloading.")
                    
                    # Create a valid filename
                    parsed_img_path = urlparse(original_img_url).path
                    img_basename = os.path.basename(parsed_img_path) if parsed_img_path else "wikipedia_image"
                    filename = re.sub(r'[^a-zA-Z0-9_\.\-]', '_', img_basename)
                    
                    # Ensure an extension
                    if not os.path.splitext(filename)[1]:
                        content_type = img_response.headers.get('content-type', '').lower()
                        if 'image/jpeg' in content_type or 'image/jpg' in content_type: filename += ".jpg"
                        elif 'image/png' in content_type: filename += ".png"
                        elif 'image/gif' in content_type: filename += ".gif"
                        elif 'image/webp' in content_type: filename += ".webp"
                        else: filename += ".img" # Generic extension

                    full_save_path = os.path.join(download_folder, filename)
                    
                    # Avoid overwriting: if file exists, add a suffix
                    counter = 1
                    temp_path = full_save_path
                    while os.path.exists(temp_path):
                        name, ext = os.path.splitext(full_save_path)
                        temp_path = f"{name}_{counter}{ext}"
                        counter += 1
                    full_save_path = temp_path
                        
                    with open(full_save_path, 'wb') as f:
                        f.write(img_data)
                    downloaded_image_paths.append(full_save_path)
                    logger.debug(f"Saved image to {full_save_path}")
                else:
                    logger.info(f"Skipping image (actual width {img.width} < {min_width}): {original_img_url}")
            
            except httpx.HTTPStatusError as e_status: # Specific error for bad status
                 logger.warning(f"HTTP error {e_status.response.status_code} downloading image {original_img_url if 'original_img_url' in locals() else img_url}: {e_status}")
            except httpx.RequestError as e_req: # Other request errors (timeout, connection, etc.)
                 logger.warning(f"Request error downloading image {original_img_url if 'original_img_url' in locals() else img_url}: {e_req}")
            except IOError: # Pillow can raise IOError for non-image files or corrupt images
                logger.warning(f"Pillow could not open or identify image from {original_img_url if 'original_img_url' in locals() else img_url}. Skipping.")
            except Exception as e_img: # Catch-all for other unexpected errors during image processing
                logger.error(f"Unexpected error processing image {original_img_url if 'original_img_url' in locals() else img_url}: {e_img}", exc_info=True)
        
        return downloaded_image_paths

# Selenium helper functions from the original file - can be refactored into the class or utils
# For now, they are not directly used by the refactored WikipediaSiteModule's get_data method above.
# They were part of the get_wikipedia_data_with_driver function which is being replaced.
# If any specific complex interaction is needed (e.g. filling forms on wikipedia), these could be adapted.

# def find_element_with_wait(...) etc.

# Original get_wikipedia_data_with_driver is now superseded by WikipediaSiteModule.get_data()

# Register module
site_registry.register('wikipedia', WikipediaSiteModule)

# Ensure WikipediaSiteModule is added to __all__ in src/sites/__init__.py
# from .wikipedia import WikipediaSiteModule
# __all__.append("WikipediaSiteModule") 