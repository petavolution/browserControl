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

from typing import Dict, Type, Any, Optional, List
from core.config import SiteConfig

# The SiteRegistry class that was here is now removed.
# The get_module logic and list_supported_sites are methods of the SiteRegistry class
# in base_site.py. Consumers will call site_registry.get_module(...)

# Example of how site modules might be registered elsewhere (e.g., in BrowserControlSystem or main.py)
# from .google_search import GoogleSearchModule
# from .amazon_search import AmazonSearchModule
# ... etc.
# site_registry.register("google", GoogleSearchModule)
# site_registry.register("amazon", AmazonSearchModule) 