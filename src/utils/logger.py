#!/usr/bin/env python3
"""
Logging System for BrowserControL01
====================================

Robust logging with security filtering, debug file output, and exception tracking.
All errors and debug output are written to debug-log.txt for easy troubleshooting.
"""

import sys
import logging
import re
from pathlib import Path
from typing import Optional


class StealthLogger:
    """Logging system with security filtering and debug file output"""

    # Class-level debug log file for all instances
    DEBUG_LOG_FILE = Path("debug-log.txt")

    def __init__(self, log_file: Path = None, level: str = "DEBUG", name: str = "stealth-system"):
        self.log_file = log_file or Path("stealth-system.log")
        self.name = name
        self.logger = self._setup_logger(level)

    def _setup_logger(self, level: str) -> logging.Logger:
        """Configure logger with file and console handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)  # Always capture everything internally

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Formatter with more detail for debugging
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        )
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s"
        )

        # Main log file handler (all levels)
        if self.log_file:
            try:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(self.log_file, mode="a", encoding="utf-8")
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not create log file handler for {self.log_file}: {e}")

        # Debug log file handler (always writes to debug-log.txt)
        try:
            debug_handler = logging.FileHandler(self.DEBUG_LOG_FILE, mode="a", encoding="utf-8")
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(file_formatter)
            logger.addHandler(debug_handler)
        except Exception as e:
            print(f"Warning: Could not create debug log handler: {e}")

        # Console handler (configurable level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_level = getattr(logging, level.upper(), logging.INFO)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def debug(self, msg: str, *args, exc_info: bool = False, **kwargs):
        """Security-filtered debug logging"""
        self.logger.debug(self._filter_sensitive(str(msg)), *args, exc_info=exc_info, **kwargs)

    def info(self, msg: str, *args, exc_info: bool = False, **kwargs):
        """Security-filtered info logging"""
        self.logger.info(self._filter_sensitive(str(msg)), *args, exc_info=exc_info, **kwargs)

    def warning(self, msg: str, *args, exc_info: bool = False, **kwargs):
        """Security-filtered warning logging"""
        self.logger.warning(self._filter_sensitive(str(msg)), *args, exc_info=exc_info, **kwargs)

    def error(self, msg: str, *args, exc_info: bool = True, **kwargs):
        """Security-filtered error logging with exception info by default"""
        self.logger.error(self._filter_sensitive(str(msg)), *args, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, *args, exc_info: bool = True, **kwargs):
        """Security-filtered critical logging with exception info"""
        self.logger.critical(self._filter_sensitive(str(msg)), *args, exc_info=exc_info, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log an exception with full traceback"""
        self.logger.exception(self._filter_sensitive(str(msg)), *args, **kwargs)

    def _filter_sensitive(self, msg: str) -> str:
        """Filter sensitive information from logs"""
        if not isinstance(msg, str):
            msg = str(msg)

        patterns = [
            (r'password["\s]*[:=]["\s]*[^"\s,}]+', 'password="***"'),
            (r'token["\s]*[:=]["\s]*[^"\s,}]+', 'token="***"'),
            (r'api[_-]?key["\s]*[:=]["\s]*[^"\s,}]+', 'api_key="***"'),
            (r'secret["\s]*[:=]["\s]*[^"\s,}]+', 'secret="***"'),
            (r'auth["\s]*[:=]["\s]*[^"\s,}]+', 'auth="***"'),
        ]

        filtered = msg
        for pattern, replacement in patterns:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)

        return filtered

    def log_separator(self, title: str = ""):
        """Log a visual separator for readability"""
        sep_line = "=" * 70
        if title:
            self.info(f"\n{sep_line}\n{title}\n{sep_line}")
        else:
            self.info(sep_line)


def get_logger(name: str = "stealth-system", log_file: Optional[Path] = None, level: str = "INFO") -> StealthLogger:
    """Get a configured logger instance

    Args:
        name: Logger name (for identification in log output)
        log_file: Path for main log file (default: stealth-system.log)
        level: Console logging level (file always logs DEBUG)

    Returns:
        StealthLogger instance
    """
    return StealthLogger(log_file=log_file, level=level, name=name)
