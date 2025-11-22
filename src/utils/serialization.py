#!/usr/bin/env python3
"""
Serialization Utilities for BrowserControL01
============================================

Provides custom JSON encoding for complex data structures used in the project.
"""

import json
from datetime import datetime, date
from dataclasses import is_dataclass, asdict
from selenium.webdriver.remote.webelement import WebElement
from pathlib import Path
from enum import Enum
from typing import Any

# Attempt to import ExtractedElement and ElementProperties. 
# This might create a circular dependency if utils is imported by core.structures.
# If that happens, these specific classes might need to be passed to the encoder
# or the encoder might need to be in a place that doesn't cause circular imports.
# For now, let's try a direct import path assuming utils is not a core dependency FOR core.

# To avoid potential circular import issues if utils were imported by core components,
# we can use isinstance checks with type names as strings initially, or pass types explicitly.
# However, for asdict to work well with dataclasses, direct type checking is better.
# Let's assume for now this util is standalone or imported by higher-level modules like main.py.

class CustomJsonEncoder(json.JSONEncoder):
    """Custom JSON Encoder for project-specific data structures."""
    def default(self, o: Any) -> Any:
        if is_dataclass(o) and not isinstance(o, type):
            # For dataclasses, convert to dict. Handle WebElement fields specifically.
            d = asdict(o)
            # Remove raw_webelement from ElementProperties before serialization
            if o.__class__.__name__ == 'ElementProperties':
                d.pop('raw_webelement', None)
            
            # Handle ExtractedElement.value if it's a WebElement
            if o.__class__.__name__ == 'ExtractedElement':
                if 'properties' in d and d['properties'] is not None and 'raw_webelement' in d['properties']:
                     d['properties'].pop('raw_webelement', None) # Ensure it's removed from nested ElementProperties
                
                element_value = getattr(o, 'value', None) # Use getattr to safely access .value
                if isinstance(element_value, WebElement):
                    d['value'] = f"<WebElement: {element_value.tag_name} id={element_value.id[:8]}...>"
            return d
        elif isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, WebElement):
            # This case should ideally be handled within the dataclass conversion,
            # but as a fallback if a WebElement is passed directly.
            return f"<WebElement: {o.tag_name} id={o.id[:8]}...> (Unserializable - should be handled in dataclass)"
        
        # Let the base class default method raise the TypeError for other types
        return super().default(o)


# Example Usage (for testing purposes, not part of the module's primary code)
if __name__ == '__main__':
    from src.core.structures import ExtractedElement, ElementProperties # Relative import for testing script
    
    print("Testing CustomJsonEncoder...")
    
    # Create a dummy WebElement-like object for testing if Selenium isn't available
    class DummyWebElement:
        def __init__(self, tag_name='div', id='dummy123456789'):
            self.tag_name = tag_name
            self.id = id

    props_with_raw = ElementProperties(
        tag_name='a',
        attributes={'href': 'https://example.com'},
        text='Click me',
        raw_webelement=DummyWebElement()
    )
    
    extracted_text = ExtractedElement(
        name='product_title',
        value='Awesome Product',
        extraction_type='text',
        source_selector='.title-class',
        properties=ElementProperties(tag_name='h1', text='Awesome Product')
    )
    
    extracted_element_val = ExtractedElement(
        name='main_image_element',
        value=DummyWebElement(tag_name='img', id='mainimg001'),
        extraction_type='element',
        source_selector='#mainImage',
        properties=ElementProperties(tag_name='img', attributes={'src':'/path.jpg'}, raw_webelement=DummyWebElement(tag_name='img', id='mainimg001'))
    )
    
    data_to_serialize = {
        "timestamp": datetime.now(),
        "item_name": "Test Item",
        "extracted_data": [
            extracted_text,
            extracted_element_val
        ],
        "raw_properties_test": props_with_raw
    }
    
    try:
        json_output = json.dumps(data_to_serialize, cls=CustomJsonEncoder, indent=4)
        print("\nSerialized JSON Output:")
        print(json_output)
    except Exception as e:
        print(f"\nError during serialization test: {e}")

    print("\nTesting direct WebElement serialization (should be caught by dataclass logic ideally):")
    try:
        direct_we_output = json.dumps(DummyWebElement(), cls=CustomJsonEncoder, indent=4)
        print(direct_we_output) # Fallback handler in encoder will produce a string
    except TypeError as te:
        print(f"Caught expected TypeError for direct WebElement: {te}") # Should not happen if fallback works
    except Exception as e:
        print(f"Error with direct WebElement: {e}") 