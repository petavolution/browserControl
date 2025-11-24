"""
Site-Specific Modules for BrowserControL01
==========================================

Specialized automation modules for major websites.
"""

from .base_site import site_registry, BaseSiteModule

# Simple imports to avoid relative import issues
from .amazon import AmazonSearchModule
from .ebay import EbaySearchModule
from .chatgpt import ChatGPTModule
from .generic_site import GenericSiteModule
from .google import GoogleSearchModule
from .wikipedia import WikipediaSiteModule

# Note: Import these directly from their modules to avoid circular imports
# Example: from sites.google import GoogleSearchModule 

# Ensure all modules are imported so they can be registered
__all__ = [
    "BaseSiteModule",
    "site_registry",
    "AmazonSearchModule",
    "EbaySearchModule",
    "ChatGPTModule",
    "GenericSiteModule",
    "GoogleSearchModule",
    "WikipediaSiteModule"
]