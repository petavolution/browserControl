#!/usr/bin/env python3
"""
Configuration Management for BrowserControL01
==============================================

Centralized configuration with simplified, focused parameters.
"""

import pathlib
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
import random

# Helper for directory creation
def ensure_directory_exists(dir_path: pathlib.Path):
    """Ensure a directory exists, creating it if necessary."""
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Consider logging this error if a logger is available here
        # For now, print as it's a critical path for config setup.
        print(f"Error creating directory {dir_path}: {e}")

@dataclass
class TimeoutConfig:
    page_load: int = 30
    element_find: int = 10
    script_execution: int = 10
    default_pause_between_actions: float = 1.0

@dataclass
class SiteConfig:
    """Configuration for site-specific modules"""
    name: str
    base_url: str
    selector_file_path: Optional[pathlib.Path] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)

    def __post_init__(self):
        if self.custom_params is None: # Should be redundant due to default_factory but good practice
            self.custom_params = {}
        if self.timeouts is None: # Should be redundant
            self.timeouts = TimeoutConfig()

@dataclass
class SystemConfig:
    """Simplified system configuration focused on core functionality"""
    
    # Core paths
    base_path: pathlib.Path = field(default_factory=lambda: pathlib.Path(__file__).resolve().parent.parent.parent) # Project root
    output_dir: Optional[pathlib.Path] = None # If None, defaults to base_path / "output"
    profile_dir: pathlib.Path = field(default_factory=lambda: pathlib.Path.home() / ".bot-profiles")
    log_file: Optional[pathlib.Path] = None # Path for logging, if None, logs to console / default.log
    log_level: str = "INFO" # DEBUG, INFO, WARNING, ERROR
    
    # Human behavior parameters
    min_interaction_time: float = 0.08
    max_interaction_time: float = 0.25
    mouse_jitter_px: int = 4
    thinking_time_range: Tuple[float, float] = (2.0, 5.0)
    
    # Session management
    default_wait_timeout: int = 20
    page_load_timeout: int = 30 # General page load timeout
    default_retry_attempts: int = 3
    default_retry_pause_sec: float = 1.0
    min_main_content_text_length: int = 100 # Min text length for an element to be considered main content by DOM interactor

    # Browser Control
    headless_mode: bool = False
    user_agent_override: Optional[str] = None
    current_profile_name: Optional[str] = "default" # Default profile to use if not specified
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])  # Browser language preferences

    # Stealth Configuration for BasicStealthManager
    enable_basic_stealth: bool = True
    spoof_hardware_concurrency: bool = True # Control for BasicStealthManager
    hardware_concurrency_value: Optional[int] = field(default_factory=lambda: random.choice([2, 4, 8, 16]))
    spoof_device_memory: bool = True # Control for BasicStealthManager
    device_memory_value: Optional[int] = field(default_factory=lambda: random.choice([2, 4, 8, 16]))
    spoof_navigator_plugins: bool = True # Renamed from spoof_plugins_mimeTypes for clarity
    spoof_webgl: bool = True # Control for BasicStealthManager
    webgl_vendor: Optional[str] = "Google Inc. (Intel)" # Renamed from webgl_vendor_override
    webgl_renderer: Optional[str] = "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics, OpenGL ES 3.0 Chromium)" # Renamed
    spoof_permissions_api: bool = True # Control for BasicStealthManager
    permissions_default_granted: List[str] = field(default_factory=lambda: ["notifications"])
    permissions_default_denied: List[str] = field(default_factory=lambda: [])
    permissions_default_prompt: List[str] = field(default_factory=lambda: ["geolocation", "camera", "microphone"])
    apply_canvas_noise: bool = True # Renamed from enable_canvas_noise
    apply_audiocontext_noise: bool = True # Renamed from enable_audiocontext_noise
    disable_webrtc: bool = True
    additional_chrome_options: List[str] = field(default_factory=list)

    # Typing behavior parameters
    typing_char_delay_config: dict = field(default_factory=lambda: {
        "base_time_multiplier": 1.0, "space_multiplier": 1.2, "punctuation_multiplier": 1.4,
        "default_char_multiplier": 1.0, "random_variation_min": 0.8, "random_variation_max": 1.3,
        "thinking_pause_char_interval_min": 15, "thinking_pause_char_interval_max": 30,
        "thinking_pause_duration_min": 0.3, "thinking_pause_duration_max": 0.8
    })

    # Mouse click parameters
    mouse_click_config: dict = field(default_factory=lambda: {
        "default_duration_min": 0.3, "default_duration_max": 0.7, "urgent_multiplier": 0.5,
        "careful_multiplier": 1.5, "pre_click_pause_min": 0.1, "pre_click_pause_max": 0.3,
        "post_click_pause_min": 0.1, "post_click_pause_max": 0.3
    })

    # Human scroll parameters
    human_scroll_config: dict = field(default_factory=lambda: {
        "short": {"repetitions": 1, "pause_between_reps_min": 0.1, "pause_between_reps_max": 0.3},
        "medium": {"repetitions_min": 3, "repetitions_max": 7, "pause_between_reps_min": 0.05, "pause_between_reps_max": 0.15},
        "long": {"repetitions": 1, "pause_between_reps_min": 0.2, "pause_between_reps_max": 0.5},
        "default_scroll_type": "medium"
    })

    # Key press parameters
    key_press_config: dict = field(default_factory=lambda: {
        "pre_press_pause_min": 0.05, "pre_press_pause_max": 0.15,
        "post_press_pause_min": 0.05, "post_press_pause_max": 0.15
    })

    # Mouse movement parameters
    mouse_move_config: dict = field(default_factory=lambda: {
        "num_intermediate_points_min": 2, "num_intermediate_points_max": 5,
        "path_deviation_factor": 0.15, "segment_duration_variation": 0.3,
        "pause_between_segments_min": 0.01, "pause_between_segments_max": 0.05
    })
    
    # Manual Intervention
    enable_manual_intervention_prompts: bool = False

    # Site Specific Configurations
    site_details: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "google": {
            "name": "Google", "base_url": "https://www.google.com", "selector_file_name_part": "google",
            "custom_params": {}, "timeouts": TimeoutConfig(page_load=15, element_find=5)
        },
        "amazon": {
            "name": "Amazon", "base_url": "https://www.amazon.com", "selector_file_name_part": "amazon",
            "custom_params": {}, "timeouts": TimeoutConfig(page_load=20, element_find=8)
        },
        "ebay": {
            "name": "Ebay", "base_url": "https://www.ebay.com", "selector_file_name_part": "ebay",
            "custom_params": {}, "timeouts": TimeoutConfig(page_load=20, element_find=8)
        },
        "wikipedia": {
            "name": "Wikipedia", "base_url": "https://www.wikipedia.org", "selector_file_name_part": "wikipedia",
            "custom_params": {}, "timeouts": TimeoutConfig(page_load=15, element_find=5)
        },
        "chatgpt": {
            "name": "ChatGPT", "base_url": "https://chat.openai.com", "selector_file_name_part": "chatgpt",
            "custom_params": {"needs_human_login_assistance": True, "chatgpt_username": None, "chatgpt_password": None}, # Added credentials here
            "timeouts": TimeoutConfig(page_load=30, element_find=15)
        }
    })

    def __post_init__(self):
        # Resolve paths relative to base_path if they are not absolute
        if self.output_dir and not self.output_dir.is_absolute():
            self.output_dir = self.base_path / self.output_dir
        elif not self.output_dir: # Default output dir if None
             self.output_dir = self.base_path / "output"
        
        if self.log_file and not self.log_file.is_absolute(): # Default log file if relative
            self.log_file = self.base_path / self.log_file
        elif not self.log_file:
            self.log_file = self.base_path / "stealth-system.log"
        
        if not self.profile_dir.is_absolute():
             if not str(self.profile_dir).startswith(str(pathlib.Path.home())):
                 self.profile_dir = pathlib.Path.home() / self.profile_dir.name
        
        ensure_directory_exists(self.profile_dir)
        if self.output_dir: # output_dir is now guaranteed to be set
            ensure_directory_exists(self.output_dir)
        
        # Ensure log directory exists
        if self.log_file:
            ensure_directory_exists(self.log_file.parent)


    def get_site_configuration_details(self, site_name: str) -> Dict[str, Any]:
        """Fetches the predefined configuration for a site."""
        details = self.site_details.get(site_name.lower())
        if not details:
            return {} # Return empty dict if not found, calling code should handle
        return details

    def get_site_config_object(self, site_name: str) -> Optional[SiteConfig]:
        """
        Constructs a SiteConfig object for a given site name using this SystemConfig instance.
        This method effectively merges general system settings with site-specific overrides.
        """
        site_params = self.get_site_configuration_details(site_name)
        if not site_params: # If no specific details, could create a generic one or return None
            # self.log.warning(f"No site-specific details for '{site_name}'. Consider adding to SystemConfig.site_details.") # Assumes log is available
            # Optionally, create a default SiteConfig for generic sites if base_url can be inferred or is not critical.
            # For now, returning None as site_name implies an expectation of pre-configuration.
            return None


        # Resolve selector_file_path relative to self.base_path / "src/sites/selectors"
        selectors_dir = self.base_path / "src" / "sites" / "selectors"
        sfn_part = site_params.get('selector_file_name_part', site_name.lower())
        default_selector_filename = f"{sfn_part}_selectors.json"
        
        # Priority: 1. selector_file_path from site_details, 2. default constructed path
        selector_file_to_check = site_params.get('selector_file_path')
        
        final_selector_path: Optional[pathlib.Path] = None
        if selector_file_to_check:
            path_obj = pathlib.Path(selector_file_to_check)
            final_selector_path = path_obj if path_obj.is_absolute() else self.base_path / path_obj
        else:
            final_selector_path = selectors_dir / default_selector_filename
            
        existing_selector_file = final_selector_path if final_selector_path and final_selector_path.exists() else None
        if not existing_selector_file and final_selector_path:
             # It's good to log if a configured or default selector file is expected but not found.
             # self.log.debug(f"Selector file not found at {final_selector_path} for site {site_name}. No selectors will be loaded.")
             pass # Allow None to be passed if file doesn't exist

        return SiteConfig(
            name=site_params.get('name', site_name.capitalize()),
            base_url=site_params.get('base_url', ""),
            selector_file_path=existing_selector_file,
            custom_params=site_params.get('custom_params', {}), # Merges with SiteConfig's default_factory
            timeouts=site_params.get('timeouts', TimeoutConfig()) # Uses SiteConfig's default factory if 'timeouts' key missing
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert SystemConfig to a dictionary for serialization/display.

        Converts Path objects to strings and handles nested dataclasses.
        """
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            # Convert Path objects to strings
            if isinstance(value, pathlib.Path):
                result[field_name] = str(value)
            # Skip large/complex nested structures for display
            elif field_name in ('site_details', 'typing_char_delay_config', 'mouse_click_config',
                               'human_scroll_config', 'key_press_config', 'mouse_move_config'):
                result[field_name] = f"<{type(value).__name__}>"
            else:
                result[field_name] = value
        return result

@dataclass
class WorkflowConfig:
    """Generic configuration for a workflow execution."""
    workflow_name: str
    site_name: str # e.g., "google", "wikipedia"
    operation: str # e.g., "search", "get_data"
    params: Dict[str, Any] = field(default_factory=dict) # Operation-specific parameters
    profile_name: Optional[str] = None # Profile to use for this workflow run
    output_options: Dict[str, Any] = field(default_factory=dict) # e.g., {"format": "json", "path": "..."} 