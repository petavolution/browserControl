#!/usr/bin/env python3
"""
Core Data Structures for BrowserControL01
===========================================

This module defines common data structures used across the system,
particularly for representing extracted data and element properties.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime

@dataclass
class ElementProperties:
    """Holds properties of a located Selenium WebElement."""
    tag_name: Optional[str] = None
    attributes: Optional[Dict[str, str]] = None
    text: Optional[str] = None # Inner text of the element
    is_displayed: Optional[bool] = None
    is_enabled: Optional[bool] = None
    location: Optional[Dict[str, int]] = None # E.g., {'x': 10, 'y': 20}
    size: Optional[Dict[str, int]] = None # E.g., {'width': 100, 'height': 50}
    raw_webelement: Any = field(default=None, repr=False) # The actual WebElement, not for direct serialization


@dataclass
class ExtractedElement:
    """
    Represents a piece of data extracted from a web page, along with its context.
    """
    name: str # The logical name given to this piece of data (e.g., 'product_title', 'price')
    value: Any # The extracted value itself (text, attribute, or even a WebElement)
    
    extraction_type: str # How the value was extracted (e.g., 'text', 'attribute:href', 'element')
    source_selector: str # The selector used to find this specific detail within its parent item
    
    properties: Optional[ElementProperties] = None # Properties of the Selenium element from which this was extracted
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Fields for heuristic/ML layers
    found_by_strategy: Optional[str] = None # Strategy used to find the element (e.g., direct, smart, content)
    semantic_role: Optional[str] = None # Semantic role identified by heuristic analysis (e.g., 'add_to_cart_button', 'product_price')
    role_confidence: Optional[float] = None # Confidence score (0.0-1.0) for the identified semantic_role
    confidence: Optional[float] = None # General confidence for the extraction itself (can be different from role_confidence)
    
    notes: List[str] = field(default_factory=list)
    
    # Indicates if the extraction was successful for this specific element
    # Useful when an ExtractedElement object is created even if extraction failed (e.g. for a required field)
    extraction_successful: bool = True

    def __post_init__(self):
        # Ensure notes is always a list
        if self.notes is None:
            self.notes = [] 