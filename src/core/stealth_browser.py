#!/usr/bin/env python3
"""
Stealth Browser Management for BrowserControL01
===============================================

Focused browser management with essential stealth capabilities.
"""

import random
import time
from contextlib import contextmanager
from typing import Optional

import undetected_chromedriver as uc
from fake_useragent import UserAgent

from .config import SystemConfig
try:
    from ..security.basic_stealth import BasicStealthManager
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


class StealthBrowserManager:
    """Simplified browser management with core stealth features"""
    
    def __init__(self, config: SystemConfig, logger):
        self.config = config
        self.log = logger
        self.driver = None
        self.user_agent = UserAgent()
        
    def launch_browser(self, profile_name: str = "default") -> bool:
        """Launch stealth browser with essential configuration"""
        try:
            self.log.info("Launching stealth browser")
            
            # Setup profile directory
            profile_path = self.config.profile_dir / profile_name
            profile_path.mkdir(parents=True, exist_ok=True)
            
            # Configure Chrome options
            options = uc.ChromeOptions()
            
            # Essential stealth arguments
            options.add_argument(f'--user-data-dir={profile_path}')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            
            # Dynamic viewport
            width = random.randint(1280, 1600)
            height = random.randint(720, 950)
            options.add_argument(f'--window-size={width},{height}')
            
            # Random user agent
            fake_ua = self.user_agent.random
            options.add_argument(f'--user-agent={fake_ua}')
            
            # Language settings
            lang_header = ",".join(self.config.languages)
            options.add_argument(f'--lang={lang_header}')
            
            # Privacy settings
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-background-timer-throttling')
            
            # Launch browser
            self.driver = uc.Chrome(
                options=options,
                headless=False,
                use_subprocess=True
            )
            
            # Apply stealth patches using BasicStealthManager if available and enabled
            if SECURITY_AVAILABLE and self.config.enable_basic_stealth:
                security_manager = BasicStealthManager(self.config, self.log)
                if not security_manager.apply_browser_stealth_patches(self.driver):
                    self.log.warning("Failed to apply security patches via BasicStealthManager. Proceeding without them.")
            elif self.config.enable_basic_stealth:
                self.log.warning("Basic stealth is enabled in config, but BasicStealthManager is not available.")
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.implicitly_wait(self.config.default_wait_timeout)
            
            self.log.info("Stealth browser launched successfully")
            return True
            
        except Exception as e:
            self.log.error(f"Failed to launch browser: {e}")
            return False
    
    def navigate_to(self, url: str, max_retries: int = None) -> bool:
        """Navigate to URL with retry logic"""
        if not self.driver:
            self.log.error("No browser session available")
            return False
        
        retries = max_retries or self.config.default_retry_attempts
        
        for attempt in range(retries):
            try:
                self.log.debug(f"Navigating to {url} (attempt {attempt + 1})")
                self.driver.get(url)
                
                # Wait for page load
                self.driver.execute_script("return document.readyState") == "complete"
                
                self.log.info(f"Successfully navigated to {url}")
                return True
                
            except Exception as e:
                self.log.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def get_page_source(self) -> Optional[str]:
        """Get current page source"""
        if not self.driver:
            return None
        
        try:
            return self.driver.page_source
        except Exception as e:
            self.log.error(f"Failed to get page source: {e}")
            return None
    
    def execute_script(self, script: str) -> Optional[any]:
        """Execute JavaScript with error handling"""
        if not self.driver:
            return None
        
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            self.log.error(f"Script execution failed: {e}")
            return None
    
    @contextmanager
    def session_context(self, profile_name: str = "default"):
        """Context manager for browser sessions"""
        try:
            if self.launch_browser(profile_name):
                yield self.driver
            else:
                yield None
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up browser session"""
        if self.driver:
            try:
                self.driver.quit()
                self.log.info("Browser session cleaned up")
            except Exception as e:
                self.log.warning(f"Cleanup error: {e}")
            finally:
                self.driver = None 