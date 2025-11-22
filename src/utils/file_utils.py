"""
File System Utilities for BrowserControL01
==========================================

Provides common file and directory manipulation functions.
"""

import os
import pathlib
import shutil
from typing import Any, Optional
# Assuming logger is available or will be passed in. For now, direct import for type hinting.
# from .logger import StealthLogger # If we need logging within utils

# Placeholder for a logger type if not wanting to import full logger here
# from ..core.logger import StealthLogger # Example, adjust if circular

# Define a generic logger type or use Any for now if StealthLogger is problematic
GenericLogger = Any # Or a more specific type if available and safe to import

def ensure_directory_exists(dir_path: pathlib.Path, logger: Optional[GenericLogger] = None) -> bool:
    """
    Ensures that a directory exists. If it doesn't, it attempts to create it.

    Args:
        dir_path: The path to the directory.
        logger: An optional logger instance for logging actions.

    Returns:
        True if the directory exists or was successfully created, False otherwise.
    """
    if dir_path.exists():
        if dir_path.is_dir():
            if logger:
                logger.debug(f"Directory already exists: {dir_path}")
            return True
        else:
            if logger:
                logger.error(f"Path exists but is not a directory: {dir_path}")
            return False
    else:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            if logger:
                logger.info(f"Successfully created directory: {dir_path}")
            return True
        except Exception as e:
            if logger:
                logger.error(f"Failed to create directory {dir_path}: {e}")
            return False

def is_valid_chrome_profile_dir(profile_path: pathlib.Path, logger: Optional[GenericLogger] = None) -> bool:
    """
    Checks if the given path appears to be a valid Chrome profile directory
    by looking for common essential files/folders.

    Args:
        profile_path: The path to the potential Chrome profile directory.
        logger: An optional logger instance.

    Returns:
        True if it seems like a valid profile directory, False otherwise.
    """
    if not profile_path.is_dir():
        if logger:
            logger.debug(f"Profile path {profile_path} is not a directory.")
        return False

    # List of essential items that should exist in a Chrome profile directory.
    # 'Preferences' and 'Cookies' are usually key.
    # 'Local Storage' and 'Session Storage' are also important for session data.
    essential_items = ["Preferences", "Cookies", "Local Storage", "Session Storage"]
    found_all_essentials = True

    for item_name in essential_items:
        item_path = profile_path / item_name
        if not item_path.exists():
            if logger:
                logger.debug(f"Essential Chrome profile item not found: {item_path}")
            found_all_essentials = False
            # We can break early if one essential is missing, but checking all might give more debug info.
            # For now, let's log and continue to see all missing items if verbose logging is on.
    
    if not found_all_essentials:
        if logger:
            logger.warning(f"Path {profile_path} is missing one or more essential Chrome profile items. It may not be a valid profile directory.")
        return False
    
    if logger:
        logger.debug(f"Path {profile_path} appears to be a valid Chrome profile directory.")
    return True

if __name__ == '__main__':
    # Example Usage
    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")

    log = DummyLogger()
    test_dir_1 = pathlib.Path("test_output_dir_1")
    test_dir_2 = pathlib.Path("test_output_dir_2/subdir")

    print(f"Ensuring {test_dir_1}...")
    ensure_directory_exists(test_dir_1, logger=log)

    print(f"Ensuring {test_dir_2}...")
    ensure_directory_exists(test_dir_2, logger=log)

    # Test with an existing file path (should fail)
    test_file_path = pathlib.Path("test_file.txt")
    with open(test_file_path, 'w') as f:
        f.write("hello")
    print(f"Ensuring {test_file_path} (should report error)...")
    ensure_directory_exists(test_file_path, logger=log)

    print("\n--- Testing Chrome Profile Path Validation ---")
    # Create a dummy valid-looking profile
    dummy_profile = pathlib.Path("dummy_chrome_profile_valid")
    dummy_profile.mkdir(exist_ok=True)
    (dummy_profile / "Preferences").touch()
    (dummy_profile / "Cookies").touch()
    (dummy_profile / "Local Storage").mkdir(exist_ok=True)
    (dummy_profile / "Session Storage").mkdir(exist_ok=True)
    print(f"Checking valid dummy profile ({dummy_profile}): {is_valid_chrome_profile_dir(dummy_profile, logger=log)}")

    # Create a dummy invalid-looking profile
    dummy_profile_invalid = pathlib.Path("dummy_chrome_profile_invalid")
    dummy_profile_invalid.mkdir(exist_ok=True)
    (dummy_profile_invalid / "Preferences").touch()
    print(f"Checking invalid dummy profile ({dummy_profile_invalid}): {is_valid_chrome_profile_dir(dummy_profile_invalid, logger=log)}")

    # Non-existent path
    non_existent_profile = pathlib.Path("i_do_not_exist_profile")
    print(f"Checking non-existent profile ({non_existent_profile}): {is_valid_chrome_profile_dir(non_existent_profile, logger=log)}")

    # Cleanup
    if test_dir_1.exists():
        shutil.rmtree(test_dir_1)
    if test_dir_2.parent.exists(): # remove "test_output_dir_2"
        shutil.rmtree(test_dir_2.parent)
    if test_file_path.exists():
        test_file_path.unlink()
    # Cleanup dummy profiles for new test
    if dummy_profile.exists():
        shutil.rmtree(dummy_profile)
    if dummy_profile_invalid.exists():
        shutil.rmtree(dummy_profile_invalid)

    print("Cleanup complete.") 