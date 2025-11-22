#!/usr/bin/env python3
"""
Human Behavior Emulation for BrowserControL01
==============================================

Realistic human behavior patterns for stealth automation.
"""

import time
import random
from typing import Optional, List, Tuple

import pyautogui
from selenium.webdriver.common.keys import Keys

from .config import SystemConfig


class HumanBehaviorEngine:
    """Simplified human behavior emulation engine"""
    
    def __init__(self, config: SystemConfig, logger):
        self.config = config
        self.log = logger
        
    def human_pause(self, min_time: Optional[float] = None, max_time: Optional[float] = None) -> None:
        """Generate human-like pause with realistic timing"""
        min_t = min_time or self.config.min_interaction_time
        max_t = max_time or self.config.max_interaction_time
        
        # Gaussian distribution for more natural timing
        mean = (min_t + max_t) / 2
        std_dev = (max_t - min_t) / 6
        
        pause_time = max(min_t, min(max_t, random.gauss(mean, std_dev)))
        time.sleep(pause_time)
    
    def thinking_pause(self) -> None:
        """Simulate human thinking/reading time"""
        min_time, max_time = self.config.thinking_time_range
        think_time = random.uniform(min_time, max_time)
        self.log.debug(f"Thinking pause: {think_time:.2f}s")
        time.sleep(think_time)
    
    def _generate_mouse_path(self, start_x: float, start_y: float, end_x: float, end_y: float, total_duration: float) -> List[Tuple[float, float, float]]:
        """Generates a list of (x, y, duration_to_reach_point) tuples for a mouse path."""
        path = []
        move_config = self.config.mouse_move_config

        num_points = random.randint(
            move_config.get("num_intermediate_points_min", 2),
            move_config.get("num_intermediate_points_max", 5)
        ) + 1 # +1 because we include the end point

        dx_total = end_x - start_x
        dy_total = end_y - start_y
        total_distance = (dx_total**2 + dy_total**2)**0.5

        current_x, current_y = start_x, start_y
        remaining_duration = total_duration

        for i in range(1, num_points + 1):
            is_last_point = (i == num_points)
            
            # Target for this segment
            target_x_segment = start_x + (dx_total * i / num_points)
            target_y_segment = start_y + (dy_total * i / num_points)

            # Calculate deviation for intermediate points
            if not is_last_point and total_distance > 0: # No deviation for the final point or if start/end are same
                deviation_factor = move_config.get("path_deviation_factor", 0.15)
                max_deviation = total_distance * deviation_factor / num_points # Scale deviation by number of points
                
                # Deviate perpendicular to the segment direction
                # Vector from current to target_segment
                seg_dx = target_x_segment - current_x
                seg_dy = target_y_segment - current_y
                seg_len = (seg_dx**2 + seg_dy**2)**0.5

                if seg_len > 0:
                    # Normalized perpendicular vector
                    perp_dx = -seg_dy / seg_len 
                    perp_dy = seg_dx / seg_len
                    
                    deviation_distance = random.uniform(-max_deviation, max_deviation)
                    actual_target_x = target_x_segment + perp_dx * deviation_distance
                    actual_target_y = target_y_segment + perp_dy * deviation_distance
                else:
                    actual_target_x = target_x_segment
                    actual_target_y = target_y_segment
            else:
                actual_target_x = end_x # Ensure the last point is exactly the end_x
                actual_target_y = end_y # Ensure the last point is exactly the end_y

            # Duration for this segment
            if is_last_point:
                segment_duration = remaining_duration
            else:
                base_segment_duration = total_duration / num_points
                variation = move_config.get("segment_duration_variation", 0.3)
                segment_duration = base_segment_duration * random.uniform(1 - variation, 1 + variation)
                segment_duration = max(0.01, min(segment_duration, remaining_duration * 0.8)) # Ensure positive and not too long
            
            path.append((actual_target_x, actual_target_y, segment_duration))
            remaining_duration -= segment_duration
            if remaining_duration < 0: remaining_duration = 0.01 # Ensure positive
            
            current_x, current_y = actual_target_x, actual_target_y
            
        # self.log.debug(f"Generated mouse path: {path}")
        return path

    def _execute_mouse_path(self, path: List[Tuple[float, float, float]]) -> None:
        """Executes a pre-generated mouse path."""
        move_config = self.config.mouse_move_config
        for i, (x, y, duration) in enumerate(path):
            pyautogui.moveTo(x, y, duration=max(0.01, duration)) # Ensure duration is positive
            if i < len(path) - 1: # Don't pause after the last segment
                pause_min = move_config.get("pause_between_segments_min", 0.01)
                pause_max = move_config.get("pause_between_segments_max", 0.05)
                if pause_max > pause_min: # Avoid error if min == max
                    time.sleep(random.uniform(pause_min, pause_max))
                elif pause_min > 0:
                    time.sleep(pause_min)

    def human_type(self, element, text: str, speed: str = "normal") -> None:
        """Type text with human-like rhythm"""
        self.log.debug(f"Typing {len(text)} characters with {speed} speed")
        
        # Speed multipliers
        speed_map = {"slow": 1.8, "normal": 1.0, "fast": 0.6, "urgent": 0.3}
        multiplier = speed_map.get(speed, 1.0)
        
        # Focus element
        self.human_click(element)
        self.human_pause(0.1, 0.3)
        
        # Type character by character
        for i, char in enumerate(text):
            element.send_keys(char)
            
            # Variable delay based on character type
            base_delay = self.config.min_interaction_time * \
                         self.config.typing_char_delay_config.get("base_time_multiplier", 1.0) * \
                         multiplier
            
            char_config = self.config.typing_char_delay_config
            if char in ' \\t\\n':
                delay = base_delay * char_config.get("space_multiplier", 1.2)
            elif char in '.,!?;:':
                delay = base_delay * char_config.get("punctuation_multiplier", 1.4)
            else:
                delay = base_delay * char_config.get("default_char_multiplier", 1.0)
            
            # Add random variation
            final_delay = delay * random.uniform(
                char_config.get("random_variation_min", 0.8), 
                char_config.get("random_variation_max", 1.3)
            )
            time.sleep(final_delay)
            
            # Occasional thinking pauses
            pause_interval_min = char_config.get("thinking_pause_char_interval_min", 15)
            pause_interval_max = char_config.get("thinking_pause_char_interval_max", 30)
            pause_duration_min = char_config.get("thinking_pause_duration_min", 0.3)
            pause_duration_max = char_config.get("thinking_pause_duration_max", 0.8)

            if i > 0 and i % random.randint(pause_interval_min, pause_interval_max) == 0:
                self.human_pause(pause_duration_min, pause_duration_max)
    
    def human_click(self, element, click_type: str = "normal") -> None:
        """Perform human-like click with mouse movement"""
        try:
            # Scroll element into view
            driver = element._parent
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            self.human_pause(0.2, 0.5)
            
            # Get element position with jitter
            location = element.location_once_scrolled_into_view
            size = element.size
            
            # Calculate click coordinates with human imprecision
            center_x = location['x'] + size['width'] / 2
            center_y = location['y'] + size['height'] / 2
            
            target_click_x = center_x + random.randint(-self.config.mouse_jitter_px, self.config.mouse_jitter_px)
            target_click_y = center_y + random.randint(-self.config.mouse_jitter_px, self.config.mouse_jitter_px)
            
            # Get current mouse position
            current_mouse_x, current_mouse_y = pyautogui.position()

            # Total duration for the mouse movement part
            click_config = self.config.mouse_click_config
            duration_min = click_config.get("default_duration_min", 0.3)
            duration_max = click_config.get("default_duration_max", 0.7)
            total_move_duration = random.uniform(duration_min, duration_max)

            if click_type == "urgent":
                total_move_duration *= click_config.get("urgent_multiplier", 0.5)
            elif click_type == "careful":
                total_move_duration *= click_config.get("careful_multiplier", 1.5)
            
            # Generate and execute the path
            mouse_path = self._generate_mouse_path(current_mouse_x, current_mouse_y, target_click_x, target_click_y, total_move_duration)
            self._execute_mouse_path(mouse_path)
            
            self.human_pause(
                click_config.get("pre_click_pause_min", 0.1), 
                click_config.get("pre_click_pause_max", 0.3)
            )
            
            # Perform click
            pyautogui.click()
            self.human_pause( # Add post-click pause from config
                click_config.get("post_click_pause_min", 0.1),
                click_config.get("post_click_pause_max", 0.3)
            )
            
        except Exception as e:
            self.log.warning(f"Mouse click failed, using Selenium fallback: {e}")
            self._selenium_click(element)
    
    def _selenium_click(self, element) -> None:
        """Fallback Selenium click"""
        click_config = self.config.mouse_click_config # Also use config for selenium click pauses
        self.human_pause(
            click_config.get("pre_click_pause_min", 0.1), 
            click_config.get("pre_click_pause_max", 0.3)
        )
        element.click()
        self.human_pause(
            click_config.get("post_click_pause_min", 0.1),
            click_config.get("post_click_pause_max", 0.3)
        )
    
    def human_scroll(self, driver, direction: str = "down", scroll_type: str = "medium", repetitions: int = 1) -> None:
        """Perform human-like scrolling by simulating key presses.

        Args:
            driver: The Selenium WebDriver instance.
            direction: "down" or "up".
            scroll_type: "short" (Arrow Key), "medium" (Arrow Key multiple times), 
                         "long" (PageDown/PageUp Key).
            repetitions: Number of times to repeat the scroll action (for medium/long scrolls).
        """
        self.log.debug(f"Human scrolling: direction={direction}, type={scroll_type}, reps={repetitions}")

        # Determine the key and default repetitions for the scroll type
        scroll_params = self.config.human_scroll_config.get(scroll_type)
        if not scroll_params:
            default_type = self.config.human_scroll_config.get("default_scroll_type", "medium")
            self.log.warning(f"Unknown scroll_type: {scroll_type}. Defaulting to {default_type} scroll.")
            scroll_params = self.config.human_scroll_config.get(default_type)
            if not scroll_params: # Should not happen if default_scroll_type is in config
                self.log.error(f"Default scroll type '{default_type}' not found in config. Aborting scroll.")
                return

        if scroll_type == "short" or scroll_type == "long":
            scroll_key = Keys.ARROW_DOWN if direction == "down" else Keys.ARROW_UP
            if scroll_type == "long":
                scroll_key = Keys.PAGE_DOWN if direction == "down" else Keys.PAGE_UP
            actual_repetitions = repetitions if repetitions > 0 else scroll_params.get("repetitions", 1)
        elif scroll_type == "medium":
            scroll_key = Keys.ARROW_DOWN if direction == "down" else Keys.ARROW_UP
            actual_repetitions = repetitions if repetitions > 0 else random.randint(
                scroll_params.get("repetitions_min", 3),
                scroll_params.get("repetitions_max", 7)
            )
        else: # Should be caught by the initial scroll_params check, but as a safeguard
            self.log.error(f"Scroll type '{scroll_type}' logic error. Aborting scroll.")
            return
        
        pause_min = scroll_params.get("pause_between_reps_min", 0.1)
        pause_max = scroll_params.get("pause_between_reps_max", 0.3)

        # Find the body element to send keys to, as it usually captures scroll events
        try:
            body = driver.find_element(by="tag name", value='body')
        except Exception as e:
            self.log.warning(f"Could not find body element to send scroll keys: {e}. Scroll might not work.")
            return

        for i in range(actual_repetitions):
            try:
                self.press_key(body, scroll_key) # Use existing press_key for its built-in pauses
                if i < actual_repetitions - 1: # Don't pause after the last repetition
                    self.human_pause(pause_min, pause_max)
            except Exception as e:
                self.log.error(f"Error during scroll key press: {e}")
                break # Stop if an error occurs
    
    def clear_and_type(self, element, text: str, speed: str = "normal") -> None:
        """Clear element and type new text"""
        try:
            element.clear()
            self.human_pause()
        except Exception:
            # Fallback: select all and delete
            element.click()
            self.human_pause()
            element.send_keys(Keys.CONTROL + "a")
            self.human_pause()
            element.send_keys(Keys.DELETE)
        
        self.human_type(element, text, speed)
    
    def press_key(self, element, key) -> None:
        """Press a key with human timing"""
        key_config = self.config.key_press_config
        self.human_pause(
            key_config.get("pre_press_pause_min", 0.05),
            key_config.get("pre_press_pause_max", 0.15)
        )
        element.send_keys(key)
        self.human_pause(
            key_config.get("post_press_pause_min", 0.05),
            key_config.get("post_press_pause_max", 0.15)
        )

    def prompt_for_manual_intervention(self, intervention_point_name: str):
        """
        If enabled in config, pauses script execution and prompts the user for manual browser interaction.
        Args:
            intervention_point_name: A descriptive name for where the intervention is occurring.
        """
        if hasattr(self.config, 'enable_manual_intervention_prompts') and self.config.enable_manual_intervention_prompts:
            self.log.info(f"MANUAL INTERVENTION POINT: {intervention_point_name}")
            print("="*70)
            print(f"🤖 Automation paused at: {intervention_point_name}")
            print("You can now manually interact with the browser window.")
            print("When you are finished, press Enter in THIS CONSOLE to resume automation.")
            print("="*70)
            input("Press Enter to resume... ")
            self.log.info(f"Resuming automation after manual intervention at: {intervention_point_name}")
        else:
            self.log.debug(f"Skipping manual intervention point (disabled in config): {intervention_point_name}") 