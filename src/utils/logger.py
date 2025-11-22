#!/usr/bin/env python3
"""
Simplified Logging System for BrowserControL01
===============================================

Streamlined logging with security-conscious output filtering.
"""

import sys
import logging
import re
from pathlib import Path


class StealthLogger:
    """Simplified logging system with security filtering"""
    
    def __init__(self, log_file: Path = None, level: str = "INFO"):
        self.log_file = log_file or Path("stealth-system.log")
        self.logger = self._setup_logger(level)
        
    def _setup_logger(self, level: str) -> logging.Logger:
        """Configure logger with file and console handlers"""
        logger = logging.getLogger("stealth-system")
        logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s"
        )
        
        # File handler
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, msg: str, *args, **kwargs):
        """Security-filtered debug logging"""
        self.logger.debug(self._filter_sensitive(msg), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Security-filtered info logging"""
        self.logger.info(self._filter_sensitive(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Security-filtered warning logging"""
        self.logger.warning(self._filter_sensitive(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Security-filtered error logging"""
        self.logger.error(self._filter_sensitive(msg), *args, **kwargs)
    
    def _filter_sensitive(self, msg: str) -> str:
        """Filter sensitive information from logs"""
        patterns = [
            (r'password["\s]*[:=]["\s]*[^"\s]+', 'password="***"'),
            (r'token["\s]*[:=]["\s]*[^"\s]+', 'token="***"'),
            (r'key["\s]*[:=]["\s]*[^"\s]+', 'key="***"'),
        ]
        
        filtered = msg
        for pattern, replacement in patterns:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        
        return filtered


def get_logger(name: str = "stealth-system", log_file: Path = None) -> StealthLogger:
    """Get a configured logger instance"""
    return StealthLogger(log_file) 