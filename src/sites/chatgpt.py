"""
ChatGPT Site Module for BrowserControL01
========================================

Handles interactions with ChatGPT as a specific site.
"""

import time
import pathlib
import datetime
from typing import Dict, Any, Optional, List

from .base_site import BaseSiteModule, site_registry
from core.config import SiteConfig, SystemConfig # Ensure SystemConfig is imported
from core.structures import ExtractedElement # Changed
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils.file_utils import ensure_directory_exists
import undetected_chromedriver as uc # For driver type hint
from logging import Logger # For logger type hint

class ChatGPTModule(BaseSiteModule):
    """Site module for interacting with ChatGPT."""

    def __init__(self, driver: uc.Chrome, config: SystemConfig, logger: Logger, site_config: SiteConfig, **kwargs):
        super().__init__(driver=driver, config=config, logger=logger, site_config=site_config, **kwargs)
        self.driver = driver
        # self.config, self.log, self.site_config are from super()
        self.log.info(f"ChatGPTModule initialized with managed WebDriver. Site: {self.site_config.name}")
        
        # Initialize output directory using the value from the loaded site_config
        output_subdir_base = self.site_config.custom_params.get('output_subdir_base', "output/chatgpt_sessions") # Changed default path
        # Ensure output_subdir_base is treated as relative to project root (self.config.base_path)
        self.output_base_dir = self.config.base_path / output_subdir_base 
        ensure_directory_exists(self.output_base_dir) # Ensure it exists at init

    # Override the 'search' method as the primary operation for this site module
    # For ChatGPT, 'search' will mean submitting a prompt.
    def search(self, query: str, **params) -> Dict[str, Any]:
        """Submits a prompt to ChatGPT and gets a response. `query` is the prompt."""
        prompt = query # For clarity within this method
        conversation_history: List[Dict[str, str]] = params.get('conversation_history', [])
        profile_name = params.get('profile', self.site_config.custom_params.get('default_profile', 'chatgpt_default'))

        current_turn_response_text: Optional[str] = None
        output_file_path: Optional[pathlib.Path] = None
        current_url_for_error = self.site_config.base_url

        conversation_history.append({'role': 'user', 'content': prompt})
        previous_assistant_responses_count = sum(1 for turn in conversation_history if turn['role'] == 'assistant')

        # Retries and pauses will be handled by find_site_element or can be passed as overrides if needed.
        # Default values will come from site_config.custom_params or system_config.

        try:
            if not self.driver or not self.is_driver_active_from_module():
                return self._create_error_result("Browser driver is not active or available for ChatGPT", current_url_for_error)
                
            current_url_for_error = self.driver.current_url

            is_first_turn = len(conversation_history) <= 1
            on_chat_page_already = self.site_config.base_url in self.driver.current_url and not self._is_login_required()

            if is_first_turn or not on_chat_page_already:
                self.log.info(f"Navigating to {self.site_config.name}: {self.site_config.base_url}")
                if not self.navigate_to_site(self.driver): 
                     return self._create_error_result(f"Failed to navigate to {self.site_config.name}", self.driver.current_url)
                self.wait_for_page_ready(self.driver)
                current_url_for_error = self.driver.current_url
                
                if self._is_login_required():
                    if not self._perform_login():
                        return self._create_error_result("Login required but failed", self.driver.current_url)
                    self.log.info("Login performed successfully.")
                    login_confirm_timeout = self.site_config.custom_params.get('login_check_timeout_sec', 15)
                    post_login_indicator_ext = self.wait_for_site_element(self.driver, "chat_page", "post_login_indicator_selector", timeout=login_confirm_timeout)
                    if not (post_login_indicator_ext and post_login_indicator_ext.value):
                        self.log.warning("Post-login indicator did not appear after login attempt.")
            else:
                self.log.info(f"Already on {self.site_config.name} site or valid session, checking for potential redirects to login.")
                if self._is_login_required():
                    if not self._perform_login():
                        return self._create_error_result("Session expired or redirected to login, and re-login failed", self.driver.current_url)
                    login_confirm_timeout = self.site_config.custom_params.get('login_check_timeout_sec', 15)
                    post_login_indicator_ext_redirect = self.wait_for_site_element(self.driver, "chat_page", "post_login_indicator_selector", timeout=login_confirm_timeout)
                    if not (post_login_indicator_ext_redirect and post_login_indicator_ext_redirect.value):
                         self.log.warning("Post-login indicator did not appear after redirected login attempt.")
                
            current_url_for_error = self.driver.current_url
            self.behavior.prompt_for_manual_intervention(f"Before sending prompt to {self.site_config.name}")

            prompt_area_ext = self.find_site_element(self.driver, "chat_page", "prompt_textarea_selector")
            if not prompt_area_ext or not prompt_area_ext.value:
                return self._create_error_result(f"Could not find prompt textarea on {self.site_config.name}", self.driver.current_url)

            self.behavior.clear_and_type(prompt_area_ext.value, prompt, speed="normal")
            self.behavior.human_pause(0.5, 1.0)

            submit_button_ext = self.find_site_element(self.driver, "chat_page", "submit_button_selector", log_not_found=False)
                                                               
            if submit_button_ext and submit_button_ext.value and submit_button_ext.properties and submit_button_ext.properties.is_displayed:
                self.behavior.human_click(submit_button_ext.value)
            else:
                self.log.info("Submit button not found or not visible, trying Enter key in prompt area.")
                self.behavior.press_key(prompt_area_ext.value, Keys.RETURN)

            current_url_for_error = self.driver.current_url
            if not self._wait_for_response_completion():
                current_turn_response_text = self._extract_latest_response(previous_assistant_responses_count)
                self.log.warning(f"Response wait timed out on {self.site_config.name}" + (", but some text extracted." if current_turn_response_text else ", and no text extracted."))
                if not current_turn_response_text:
                    return self._create_error_result("Response wait timed out and no text extracted", self.driver.current_url)
            else:
                current_turn_response_text = self._extract_latest_response(previous_assistant_responses_count)

            if not current_turn_response_text:
                return self._create_error_result(f"Failed to extract response text from {self.site_config.name}", self.driver.current_url)

            conversation_history.append({'role': 'assistant', 'content': current_turn_response_text})
            output_file_path = self._save_interaction(conversation_history, prompt)
            self.behavior.prompt_for_manual_intervention(f"After processing {self.site_config.name} response (Output: {output_file_path})")

            return self._create_success_result(data={
                'prompt': prompt,
                'response': current_turn_response_text,
                'conversation_history': conversation_history,
                'output_file': str(output_file_path) if output_file_path else None,
                'details_url': self.driver.current_url
            })

        except Exception as e:
            self.log.error(f"{self.site_config.name} interaction workflow failed: {e}", exc_info=True)
            error_data = None
            prompt_in_exception = prompt if 'prompt' in locals() else "unknown_prompt_due_to_early_error"
            if current_turn_response_text: 
                 conversation_history.append({'role': 'assistant', 'content': f"[PARTIAL RESPONSE DUE TO ERROR]\\n{current_turn_response_text}"})
            elif not any(turn['role'] == 'assistant' for turn in conversation_history[-len(conversation_history) + previous_assistant_responses_count:]):
                 conversation_history.append({'role': 'assistant', 'content': "[NO RESPONSE THIS TURN DUE TO ERROR]"})
            if conversation_history:
                saved_path = self._save_interaction(conversation_history, prompt_in_exception)
                error_data = {'conversation_history_saved_to': str(saved_path) if saved_path else None, 'partial_history': conversation_history}
            
            return self._create_error_result(error_message=f"{self.site_config.name} workflow error: {type(e).__name__} - {str(e)}", current_url=current_url_for_error, data=error_data)

    def _is_login_required(self) -> bool:
        # Check for post-login indicator first.
        post_login_indicator_ext = self.find_site_element(self.driver, 
                                                          "chat_page", 
                                                          "post_login_indicator_selector", 
                                                          retries=1, 
                                                          pause_sec=0.2, 
                                                          log_not_found=False)
        if post_login_indicator_ext and post_login_indicator_ext.value and post_login_indicator_ext.properties and post_login_indicator_ext.properties.is_displayed:
            self.log.info("Post-login indicator found. Assuming already logged in.")
            return False
        
        if "login" in self.driver.current_url.lower() or "auth" in self.driver.current_url.lower():
             self.log.info(f"Current URL ({self.driver.current_url}) suggests a login/auth page.")
             login_page_id_ext_check = self.find_site_element(self.driver, "login_page", "identifier_selector", retries=0, log_not_found=False)
             if login_page_id_ext_check and login_page_id_ext_check.value:
                 return True
             return True 

        login_page_id_ext = self.find_site_element(self.driver, "login_page", "identifier_selector", retries=1, pause_sec=0.2, log_not_found=False)
        if login_page_id_ext and login_page_id_ext.value:
            self.log.info("Login page identifier found.")
            return True
            
        username_field_ext = self.find_site_element(self.driver, "login_page", "username_input_selector", retries=1, pause_sec=0.2, log_not_found=False)
        if username_field_ext and username_field_ext.value:
            self.log.info("Username input field found on page, assuming login required.")
            return True
            
        self.log.info("Could not definitively determine if login is required. Assuming not, or handled by navigation.")
        return False

    def _perform_login(self) -> bool:
        self.log.info(f"Attempting login for {self.site_config.name}...")
        username = getattr(self.config, 'chatgpt_username', None)
        password = getattr(self.config, 'chatgpt_password', None)
        
        if not username or not password:
            self.log.warning(f"Username or password for {self.site_config.name} not configured. Cannot attempt login.")
            return False

        username_field_ext = self.find_site_element(self.driver, "login_page", "username_input_selector")
        if not (username_field_ext and username_field_ext.value): 
            self.log.error(f"Could not find username field for {self.site_config.name}.")
            return False
        self.behavior.clear_and_type(username_field_ext.value, username, speed="fast")
        self.behavior.human_pause(0.3, 0.6)

        password_field_ext = self.find_site_element(self.driver, "login_page", "password_input_selector", retries=1, pause_sec=0.1, log_not_found=False) 
        password_field_selenium_elem = None # To store the selenium element for later use with press_key

        if not (password_field_ext and password_field_ext.value and password_field_ext.properties and password_field_ext.properties.is_displayed):
            self.log.debug("Password field not immediately visible. Trying to click initial submit/continue button.")
            initial_submit_button_ext = self.find_site_element(self.driver, "login_page", "submit_button_selector") 
            if initial_submit_button_ext and initial_submit_button_ext.value:
                self.behavior.human_click(initial_submit_button_ext.value)
                password_field_wait_timeout = self.site_config.custom_params.get('login_check_timeout_sec',15)//2
                password_field_ext_after_wait = self.wait_for_site_element(self.driver, "login_page", "password_input_selector", timeout=password_field_wait_timeout)
                
                if password_field_ext_after_wait and password_field_ext_after_wait.value:
                    self.behavior.clear_and_type(password_field_ext_after_wait.value, password, speed="fast") 
                    password_field_selenium_elem = password_field_ext_after_wait.value # Store selenium element
                else:
                    self.log.error(f"Password field did not appear after clicking initial submit for {self.site_config.name}.")
                    return False
            else:
                self.log.error(f"Could not find initial submit button or password field for {self.site_config.name}.")
                return False
        else: 
            self.behavior.clear_and_type(password_field_ext.value, password, speed="fast")
            password_field_selenium_elem = password_field_ext.value # Store selenium element
            
        self.behavior.human_pause(0.3, 0.6)

        final_login_button_ext = self.find_site_element(self.driver, "login_page", "submit_button_selector") 
        if final_login_button_ext and final_login_button_ext.value:
            self.behavior.human_click(final_login_button_ext.value)
        else:
            self.log.info("Final login button not found, trying Enter in password field.")
            if password_field_selenium_elem: # Use the stored selenium element
                self.behavior.press_key(password_field_selenium_elem, Keys.RETURN)
            else:
                self.log.error("Cannot press Enter as password field reference is lost or not interactable.")
                return False

        login_timeout = self.site_config.custom_params.get('login_check_timeout_sec', 15)
        post_login_ext = self.wait_for_site_element(self.driver, "chat_page", "post_login_indicator_selector", timeout=login_timeout)
        
        if post_login_ext and post_login_ext.value: 
            self.log.info(f"Post-login indicator found. {self.site_config.name} login successful.")
            return True
        else:
            self.log.error(f"Login failed for {self.site_config.name}: Post-login indicator not found after {login_timeout}s.")
            return False

    def _wait_for_response_completion(self) -> bool:
        self.log.debug(f"Waiting for {self.site_config.name} response to complete...")
        completion_timeout = self.site_config.custom_params.get('response_completion_timeout_sec', 60)
        check_interval = self.site_config.custom_params.get('response_check_interval_sec', 2)
        
        start_time = time.time()
        while time.time() - start_time < completion_timeout:
            stop_generating_ext = self.find_site_element(self.driver, "chat_page", "stop_generating_button_selector", retries=0, pause_sec=0.1, log_not_found=False)
            if stop_generating_ext and stop_generating_ext.value and stop_generating_ext.properties and stop_generating_ext.properties.is_displayed:
                self.log.debug(f"Stop generating button found ({stop_generating_ext.source_selector}). Still waiting...")
                time.sleep(check_interval)
                continue
            
            submit_button_state_ext = self.find_site_element(self.driver, "chat_page", "submit_button_selector", retries=0, pause_sec=0.1, log_not_found=False)
            if submit_button_state_ext and submit_button_state_ext.value and submit_button_state_ext.properties and submit_button_state_ext.properties.is_enabled:
                self.log.info(f"Response likely complete: Submit button ({submit_button_state_ext.source_selector}) is enabled.")
                return True
            
            self.log.debug(f"Polling for response completion... No stop button, submit not definitively ready.")
            time.sleep(check_interval)

        self.log.warning(f"Timeout ({completion_timeout}s) waiting for response completion indicators.")
        return False

    def _extract_latest_response(self, previous_response_count: int = 0) -> Optional[str]:
        self.log.debug(f"Extracting latest response from {self.site_config.name}. Previous assistant responses: {previous_response_count}")
        
        assistant_message_selector = self.get_selector("chat_page", "assistant_message_selector")
        if not assistant_message_selector:
            self.log.error("Selector for 'assistant_message_selector' not found. Cannot extract responses.")
            return None

        try:
            all_assistant_messages_ext_list = self.dom.find_elements_with_retry(
                self.driver,
                selector=assistant_message_selector,
                element_description="assistant message block",
                min_expected=previous_response_count + 1,
                retries=2,
                pause_sec=1.0
            )

            if not all_assistant_messages_ext_list or len(all_assistant_messages_ext_list) <= previous_response_count:
                self.log.warning(f"Could not find new assistant messages. Found: {len(all_assistant_messages_ext_list) if all_assistant_messages_ext_list else 0}, Expected > {previous_response_count}")
                selenium_elements = self.driver.find_elements(By.CSS_SELECTOR, assistant_message_selector)
                if len(selenium_elements) > previous_response_count:
                    latest_response_element = selenium_elements[-1]
                    response_text = latest_response_element.text
                    self.log.info(f"Extracted latest response (fallback find_elements): '{response_text[:100]}...'")
                    return response_text.strip()
                self.log.error("Still no new assistant messages found with fallback.")
                return None

            latest_response_ext_elem = all_assistant_messages_ext_list[-1]
            
            if latest_response_ext_elem.value:
                response_text = latest_response_ext_elem.value.text
                self.log.info(f"Extracted latest response: '{response_text[:100]}...'")
                return response_text.strip()
            else:
                self.log.error(f"Latest assistant message element (source: {latest_response_ext_elem.source_selector}) found by find_elements_with_retry, but its .value (Selenium element) is None.")
                return None

        except Exception as e:
            self.log.error(f"Error extracting latest response: {e}", exc_info=True)
            return None

    def _save_interaction(self, conversation_history: List[Dict[str, str]], prompt_for_filename: str) -> Optional[pathlib.Path]:
        if not ensure_directory_exists(self.output_base_dir, self.log):
            return None
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt_stub = "".join(c if c.isalnum() else "_" for c in prompt_for_filename[:30]).strip("_") or "conversation"
        filename = f"{timestamp}_{safe_prompt_stub}.txt"
        file_path = self.output_base_dir / filename
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Conversation History ({self.site_config.name} - {filename})\nTimestamp: {timestamp}\n{'='*40}\n\n")
                for turn in conversation_history:
                    f.write(f"{turn.get('role', 'N/A').capitalize()}:\n{'-'*20}\n{turn.get('content', '')}\n\n")
            self.log.info(f"Saved conversation to: {file_path}")
            return file_path
        except Exception as e:
            self.log.error(f"Failed to save to {file_path}: {e}")
            return None

# Register module
site_registry.register('chatgpt', ChatGPTModule)