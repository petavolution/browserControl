"""
Security Components for BrowserControL01
========================================

Optional security and monitoring features.
"""

try:
    from .basic_stealth import BasicStealthManager
    BASIC_STEALTH_AVAILABLE = True
except ImportError:
    BASIC_STEALTH_AVAILABLE = False

__all__ = []
if BASIC_STEALTH_AVAILABLE:
    __all__.append('BasicStealthManager') 